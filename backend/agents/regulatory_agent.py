import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core import metrics
from backend.db.models import RegulatoryDocument, RegulatoryImpact, Contract
from backend.services.document_service import process_regulatory_document
from backend.services.embedding_service import get_single_embedding
from backend.db.milvus_client import search_contracts

logger = get_logger(__name__)


async def fetch_and_hash_url(url: str) -> Optional[tuple[bytes, str]]:
    """Fetch URL content and return (content, hash)."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    content_hash = hashlib.sha256(content).hexdigest()
                    return content, content_hash
    except Exception as e:
        logger.error("Failed to fetch URL", url=url, error=str(e))
    return None, None


async def detect_regulatory_changes(
    db: AsyncSession,
    url: str,
    source_name: str,
) -> Dict[str, Any]:
    """Check if a regulatory source has changed since last check."""
    content, content_hash = await fetch_and_hash_url(url)
    if not content:
        return {"changed": False, "error": "Could not fetch URL"}

    # Check existing hash in DB
    result = await db.execute(
        select(RegulatoryDocument)
        .where(RegulatoryDocument.source_url == url)
        .order_by(RegulatoryDocument.created_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()

    if existing and existing.content_hash == content_hash:
        logger.info("No changes detected", source=source_name, url=url)
        return {"changed": False, "source_name": source_name, "url": url}

    # Changes detected or first time seeing this source
    import uuid
    reg_doc_id = str(uuid.uuid4())

    change_summary = ""
    if existing:
        # Generate change summary using LLM
        change_summary = await _summarize_regulatory_changes(
            source_name=source_name,
            new_content_preview=content[:3000].decode("utf-8", errors="ignore"),
        )

    # Store new document record
    reg_doc = RegulatoryDocument(
        id=uuid.UUID(reg_doc_id),
        source_url=url,
        source_name=source_name,
        content_hash=content_hash,
        has_changes_from_previous=existing is not None,
        change_summary=change_summary,
        document_date=datetime.utcnow(),
    )
    db.add(reg_doc)
    await db.flush()

    # Process and index in Milvus
    import tempfile, os
    suffix = ".pdf" if b"%PDF" in content[:10] else ".html"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(content)
        temp_path = f.name

    try:
        process_result = await process_regulatory_document(
            url=url,
            regulatory_doc_id=reg_doc_id,
            source_name=source_name,
            document_date=datetime.utcnow().isoformat(),
        )
        reg_doc.chunk_count = process_result.get("chunk_count", 0)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    await db.commit()

    return {
        "changed": True,
        "source_name": source_name,
        "url": url,
        "regulatory_doc_id": reg_doc_id,
        "change_summary": change_summary,
        "is_first_time": existing is None,
    }


async def _summarize_regulatory_changes(
    source_name: str,
    new_content_preview: str,
) -> str:
    """Use Groq to generate a brief change summary."""
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": "You summarize regulatory document changes for legal compliance teams. Be concise and focus on what changed and why it matters.",
                },
                {
                    "role": "user",
                    "content": f"New/updated regulatory document from {source_name}. Summarize key points in 2-3 sentences:\n\n{new_content_preview[:2000]}",
                },
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("Change summary generation failed", error=str(e))
        return f"New regulatory update detected from {source_name}."


async def map_regulation_to_contracts(
    db: AsyncSession,
    regulatory_doc_id: str,
    change_summary: str,
    source_name: str,
) -> List[Dict[str, Any]]:
    """Find contracts affected by a regulatory change."""
    # Embed the change summary to find related contract content
    query_embedding = await get_single_embedding(
        f"legal compliance requirements: {change_summary}"
    )

    # Search contracts collection
    contract_hits = search_contracts(
        query_embedding=query_embedding,
        top_k=20,
    )

    if not contract_hits:
        return []

    # Get unique contract IDs
    contract_ids = list(set([
        hit.get("entity", {}).get("contract_id") or hit.get("contract_id", "")
        for hit in contract_hits
        if hit.get("entity", {}).get("contract_id") or hit.get("contract_id")
    ]))

    impacts = []
    import uuid

    for contract_id in contract_ids[:10]:  # Process top 10 affected contracts
        # Get contract details
        result = await db.execute(
            select(Contract).where(Contract.id == uuid.UUID(contract_id))
        )
        contract = result.scalar_one_or_none()
        if not contract:
            continue

        # Generate impact assessment
        impact_description = await _assess_regulatory_impact(
            change_summary=change_summary,
            source_name=source_name,
            contract_filename=contract.original_filename,
            contract_type=contract.contract_type or "general",
        )

        # Determine severity
        severity_keywords = {
            "critical": ["immediate", "mandatory", "penalty", "violation", "prohibited"],
            "high": ["required", "must", "shall", "compliance deadline"],
            "medium": ["recommended", "should", "guidance"],
            "low": ["may", "optional", "encouraged"],
        }

        severity = "medium"
        impact_lower = impact_description.lower()
        for level, keywords in severity_keywords.items():
            if any(k in impact_lower for k in keywords):
                severity = level
                break

        impact = RegulatoryImpact(
            regulatory_document_id=uuid.UUID(regulatory_doc_id),
            contract_id=uuid.UUID(contract_id),
            impact_description=impact_description,
            severity=severity,
            compliance_gap=f"Review required due to {source_name} update",
            recommended_action="Review contract clauses against updated regulatory requirements",
        )
        db.add(impact)

        impacts.append({
            "contract_id": contract_id,
            "contract_filename": contract.original_filename,
            "impact_description": impact_description,
            "severity": severity,
        })

    await db.commit()
    logger.info("Regulatory impact mapping complete", impacts=len(impacts))
    return impacts


async def _assess_regulatory_impact(
    change_summary: str,
    source_name: str,
    contract_filename: str,
    contract_type: str,
) -> str:
    """Generate specific impact assessment for a contract."""
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            max_tokens=200,
            messages=[
                {
                    "role": "system",
                    "content": "You assess the impact of regulatory changes on specific contracts. Be specific and actionable.",
                },
                {
                    "role": "user",
                    "content": f"Regulatory change from {source_name}: {change_summary[:500]}\n\nContract: {contract_filename} (type: {contract_type})\n\nWhat specific clauses in this contract may need review? Answer in 2-3 sentences.",
                },
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("Regulatory impact assessment failed", error=str(e))
        return f"Contract may be affected by {source_name} regulatory update. Manual review recommended."


async def run_regulatory_monitoring_cycle(db: AsyncSession) -> Dict[str, Any]:
    """Run one full monitoring cycle for all configured regulatory sources."""
    sources = settings.regulatory_source_list
    if not sources:
        logger.info("No regulatory sources configured")
        return {"sources_checked": 0, "changes_detected": 0, "contracts_impacted": 0}

    changes_detected = 0
    total_impacts = 0

    for url in sources:
        source_name = _extract_source_name(url)
        logger.info("Checking regulatory source", source=source_name)

        change_result = await detect_regulatory_changes(db, url, source_name)

        if change_result.get("changed"):
            changes_detected += 1
            reg_doc_id = change_result.get("regulatory_doc_id", "")
            change_summary = change_result.get("change_summary", "")

            if reg_doc_id:
                impacts = await map_regulation_to_contracts(
                    db=db,
                    regulatory_doc_id=reg_doc_id,
                    change_summary=change_summary,
                    source_name=source_name,
                )
                total_impacts += len(impacts)

    metrics.regulatory_check_completed(
        source_name="all_sources",
        changed=changes_detected > 0,
        contracts_impacted=total_impacts,
        duration_seconds=0,
    )
    return {
        "sources_checked": len(sources),
        "changes_detected": changes_detected,
        "contracts_impacted": total_impacts,
        "checked_at": datetime.utcnow().isoformat(),
    }


def _extract_source_name(url: str) -> str:
    """Extract a readable source name from URL."""
    if "sebi" in url.lower():
        return "SEBI"
    elif "rbi" in url.lower():
        return "RBI"
    elif "mca" in url.lower():
        return "MCA"
    elif "gdpr" in url.lower():
        return "GDPR"
    else:
        from urllib.parse import urlparse
        return urlparse(url).netloc or url[:50]
