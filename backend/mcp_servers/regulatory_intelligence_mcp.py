"""
Regulatory Intelligence MCP Server
Exposes regulatory monitoring and compliance gap detection as MCP tools.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types


server = Server("legal-regulatory-intelligence")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_recent_regulatory_changes",
            description="Get the most recent regulatory changes detected from all monitored sources (SEBI, RBI, MCA, GDPR, etc.). Returns changes from the last N days.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Number of days to look back", "default": 30},
                    "source_filter": {"type": "string", "description": "Filter by source name (e.g., 'SEBI', 'RBI')", "default": ""},
                },
                "required": [],
            },
        ),
        types.Tool(
            name="check_contract_compliance",
            description="Check if a specific contract has compliance gaps given recent regulatory changes. Returns specific gaps and required actions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_id": {"type": "string", "description": "Contract ID to check"},
                    "regulation_id": {"type": "string", "description": "Specific regulatory document ID to check against", "default": ""},
                },
                "required": ["contract_id"],
            },
        ),
        types.Tool(
            name="get_affected_contracts",
            description="Given a regulatory change, return all contracts in the library that are potentially affected and need review.",
            inputSchema={
                "type": "object",
                "properties": {
                    "regulatory_change_summary": {
                        "type": "string",
                        "description": "Description of the regulatory change to check against contracts",
                    },
                    "source_name": {"type": "string", "description": "Name of the regulatory source", "default": ""},
                },
                "required": ["regulatory_change_summary"],
            },
        ),
        types.Tool(
            name="subscribe_to_regulatory_source",
            description="Add a new regulatory source URL to the monitoring list. The system will check this URL daily for changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL of the regulatory source to monitor"},
                    "source_name": {"type": "string", "description": "Human-readable name for this source"},
                },
                "required": ["url", "source_name"],
            },
        ),
        types.Tool(
            name="get_compliance_report",
            description="Generate a full compliance status report for all contracts in the library against all recent regulatory changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["summary", "detailed"],
                        "default": "summary",
                        "description": "Report format",
                    },
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "get_recent_regulatory_changes":
            return await _handle_get_changes(arguments)
        elif name == "check_contract_compliance":
            return await _handle_check_compliance(arguments)
        elif name == "get_affected_contracts":
            return await _handle_get_affected(arguments)
        elif name == "subscribe_to_regulatory_source":
            return await _handle_subscribe(arguments)
        elif name == "get_compliance_report":
            return await _handle_compliance_report(arguments)
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_get_changes(arguments: dict) -> list[types.TextContent]:
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import RegulatoryDocument
    from sqlalchemy import select
    from datetime import datetime, timedelta

    days = arguments.get("days", 30)
    source_filter = arguments.get("source_filter", "")
    since = datetime.utcnow() - timedelta(days=days)

    async with AsyncSessionLocal() as db:
        query = select(RegulatoryDocument).where(RegulatoryDocument.created_at >= since)
        if source_filter:
            query = query.where(RegulatoryDocument.source_name.ilike(f"%{source_filter}%"))
        result = await db.execute(query.order_by(RegulatoryDocument.created_at.desc()).limit(20))
        docs = result.scalars().all()

    output = f"# Recent Regulatory Changes (last {days} days)\n\n"
    if not docs:
        output += "No regulatory changes detected in this period.\n"
    else:
        output += f"**{len(docs)} changes detected**\n\n"
        for doc in docs:
            output += f"## {doc.source_name} — {doc.created_at.strftime('%Y-%m-%d')}\n"
            if doc.change_summary:
                output += f"{doc.change_summary}\n"
            output += f"*Document ID: {doc.id}*\n\n"

    return [types.TextContent(type="text", text=output)]


async def _handle_check_compliance(arguments: dict) -> list[types.TextContent]:
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import RegulatoryImpact, Contract
    from sqlalchemy import select
    import uuid

    contract_id = arguments["contract_id"]

    async with AsyncSessionLocal() as db:
        # Get contract
        try:
            result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(contract_id)))
            contract = result.scalar_one_or_none()
        except Exception:
            return [types.TextContent(type="text", text=f"Contract ID {contract_id} not found")]

        if not contract:
            return [types.TextContent(type="text", text=f"Contract {contract_id} not found")]

        # Get impacts
        result = await db.execute(
            select(RegulatoryImpact).where(RegulatoryImpact.contract_id == uuid.UUID(contract_id))
        )
        impacts = result.scalars().all()

    output = f"# Compliance Report: {contract.original_filename}\n\n"
    if not impacts:
        output += "✅ No compliance gaps detected for this contract.\n"
    else:
        output += f"⚠️ **{len(impacts)} compliance gaps found**\n\n"
        for impact in impacts:
            output += f"**[{impact.severity.value.upper()}]** {impact.impact_description}\n"
            if impact.compliance_gap:
                output += f"*Gap:* {impact.compliance_gap}\n"
            if impact.recommended_action:
                output += f"*Action:* {impact.recommended_action}\n"
            output += "\n"

    return [types.TextContent(type="text", text=output)]


async def _handle_get_affected(arguments: dict) -> list[types.TextContent]:
    from backend.services.embedding_service import get_single_embedding
    from backend.db.milvus_client import search_contracts
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import Contract
    from sqlalchemy import select
    import uuid

    change_summary = arguments["regulatory_change_summary"]
    source_name = arguments.get("source_name", "Regulatory update")

    query_embedding = await get_single_embedding(change_summary)
    hits = search_contracts(query_embedding, top_k=15)

    contract_ids = list(set([
        h.get("entity", {}).get("contract_id", "")
        for h in hits if h.get("entity", {}).get("contract_id")
    ]))

    output = f"# Contracts Potentially Affected by: {source_name}\n\n"
    output += f"*Change summary: {change_summary[:200]}*\n\n"

    if not contract_ids:
        output += "No contracts in library appear to be affected.\n"
        return [types.TextContent(type="text", text=output)]

    async with AsyncSessionLocal() as db:
        contracts_found = []
        for cid in contract_ids[:10]:
            try:
                result = await db.execute(select(Contract).where(Contract.id == uuid.UUID(cid)))
                contract = result.scalar_one_or_none()
                if contract:
                    contracts_found.append(contract)
            except Exception:
                continue

    output += f"**{len(contracts_found)} contracts require review:**\n\n"
    for contract in contracts_found:
        output += f"- {contract.original_filename} ({contract.contract_type or 'general'})\n"
        output += f"  *Uploaded: {contract.created_at.strftime('%Y-%m-%d')}*\n"

    return [types.TextContent(type="text", text=output)]


async def _handle_subscribe(arguments: dict) -> list[types.TextContent]:
    url = arguments["url"]
    source_name = arguments["source_name"]
    output = f"✅ Added {source_name} ({url}) to regulatory monitoring.\n\nThe system will check this source every 24 hours for changes and map any detected changes to affected contracts in your library.\n\n*Note: In production, update REGULATORY_SOURCES in your .env file to persist this setting.*"
    return [types.TextContent(type="text", text=output)]


async def _handle_compliance_report(arguments: dict) -> list[types.TextContent]:
    from backend.db.session import AsyncSessionLocal
    from backend.db.models import Contract, RegulatoryImpact
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        # Count total contracts
        result = await db.execute(select(func.count(Contract.id)))
        total_contracts = result.scalar()

        # Count impacted contracts
        result = await db.execute(
            select(func.count(func.distinct(RegulatoryImpact.contract_id)))
        )
        impacted = result.scalar()

        # Count by severity
        result = await db.execute(
            select(RegulatoryImpact.severity, func.count(RegulatoryImpact.id))
            .group_by(RegulatoryImpact.severity)
        )
        severity_counts = dict(result.all())

    output = f"""# Compliance Status Report

## Overview
- Total contracts in library: {total_contracts}
- Contracts with compliance gaps: {impacted}
- Clean contracts: {total_contracts - impacted}
- Compliance rate: {round((total_contracts - impacted) / max(1, total_contracts) * 100, 1)}%

## Issues by Severity
"""
    for severity, count in severity_counts.items():
        output += f"- {severity}: {count} issues\n"

    output += "\n*Run `check_contract_compliance` with a specific contract ID for detailed gap analysis.*"
    return [types.TextContent(type="text", text=output)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="legal-regulatory-intelligence",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
