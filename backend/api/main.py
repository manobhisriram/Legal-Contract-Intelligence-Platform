# Datadog APM must be initialised BEFORE all other imports
# so ddtrace can monkey-patch FastAPI, SQLAlchemy, httpx at import time
from backend.core.datadog_setup import init_datadog_apm
init_datadog_apm()

import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from backend.core.config import settings
from backend.core.logging import get_logger, setup_logging
from backend.core import metrics
from backend.db.session import get_db, create_tables
from backend.db.milvus_client import initialize_all_collections
from backend.db.models import (
    Contract, ContractReview, ExtractedClause, RegulatoryDocument,
    RegulatoryImpact, EvaluationRun, RedTeamRun, ReviewStatus
)
from backend.services.document_service import process_contract_document
from backend.services.embedding_service import get_single_embedding, rewrite_query_for_search, rerank_chunks
from backend.agents.contract_review_agent import run_full_contract_review
from backend.agents.regulatory_agent import run_regulatory_monitoring_cycle
from backend.agents.llm_judge import run_benchmark_evaluation
from backend.agents.red_team_agent import run_red_team_evaluation, generate_patch_recommendations
from backend.db.milvus_client import search_contracts, check_semantic_cache, store_in_cache, contract_filter

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Legal Intelligence Agent API", version=settings.app_version)
    try:
        await create_tables()
        initialize_all_collections()
        logger.info("Startup complete — APM, DB, Milvus ready")
    except Exception as e:
        logger.error("Startup failed", error=str(e))
    yield
    logger.info("Shutting down Legal Intelligence Agent")


app = FastAPI(
    title="Autonomous Legal Intelligence Agent",
    description="Multi-modal legal document analysis with multi-agent contract review, regulatory monitoring, MCP tool servers and Datadog observability",
    version=settings.app_version,
    lifespan=lifespan,
)

_cors_origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Credentialed requests are only meaningful with an explicit origin allow-list.
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request metrics middleware ───────────────────────────────────────────────

@app.middleware("http")
async def datadog_request_metrics_middleware(request: Request, call_next):
    """
    Records API latency, status codes, and error rates to Datadog
    for every HTTP request. Supplements what ddtrace auto-instruments
    with business-context tags.
    """
    start_ms = time.time() * 1000
    endpoint = request.url.path
    method = request.method

    try:
        response: Response = await call_next(request)
        latency_ms = time.time() * 1000 - start_ms
        metrics.api_request_completed(
            endpoint=endpoint,
            method=method,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )
        # Add Datadog trace ID to response headers for correlation
        try:
            from ddtrace import tracer
            span = tracer.current_span()
            if span:
                response.headers["X-Datadog-Trace-Id"] = str(span.trace_id)
        except Exception:
            pass
        return response
    except Exception:
        latency_ms = time.time() * 1000 - start_ms
        metrics.api_request_completed(
            endpoint=endpoint,
            method=method,
            status_code=500,
            latency_ms=latency_ms,
        )
        raise


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class ContractUploadResponse(BaseModel):
    contract_id: str
    filename: str
    total_chunks: int
    pages_with_vision: int
    has_vision_processing: bool
    message: str


def _validate_uuid(value: Optional[str]) -> Optional[str]:
    """Reject anything that is not a UUID before it reaches a database or vector-store filter."""
    if value is None:
        return value
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise ValueError("contract_id must be a valid UUID")


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(400, "Invalid contract identifier")


class ContractReviewRequest(BaseModel):
    contract_id: str
    contract_type: str = "general"

    _check_contract_id = field_validator("contract_id")(_validate_uuid)


class ContractReviewResponse(BaseModel):
    contract_id: str
    review_id: str
    overall_risk_level: str
    overall_risk_score: float
    executive_summary: str
    total_clauses_found: int
    high_risk_count: int
    critical_count: int
    top_5_issues: List[dict]
    negotiation_priorities: List[str]
    deal_breakers: List[str]
    confidence_score: float
    review_duration_seconds: float
    total_cost_usd: float
    models_used: List[str]


class SearchRequest(BaseModel):
    query: str
    contract_id: Optional[str] = None
    top_k: int = 5

    _check_contract_id = field_validator("contract_id")(_validate_uuid)


class SearchResponse(BaseModel):
    query: str
    rewritten_query: str
    results: List[dict]
    cache_hit: bool
    total_cost_usd: float


class RegulatoryCheckResponse(BaseModel):
    sources_checked: int
    changes_detected: int
    contracts_impacted: int
    checked_at: str


class EvaluationRequest(BaseModel):
    contract_ids: Optional[List[str]] = None
    use_benchmark: bool = True


class RedTeamRequest(BaseModel):
    iteration: int = 1


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    from backend.core.datadog_setup import statsd
    statsd.increment("legal_intel.health.checks")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "datadog_apm": settings.dd_trace_enabled,
    }


# ─── Contract Upload ──────────────────────────────────────────────────────────

@app.post("/api/contracts/upload", response_model=ContractUploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    contract_type: str = Form(default="general"),
    enable_vision: bool = Form(default=True),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(400, "Supported formats: PDF, DOCX, TXT")

    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB upload limit")

    contract_id = str(uuid.uuid4())
    metrics.upload_started(contract_type, enable_vision)
    start_time = time.time()

    suffix = os.path.splitext(file.filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    contract = Contract(
        id=uuid.UUID(contract_id),
        filename=f"{contract_id}{suffix}",
        original_filename=file.filename,
        contract_type=contract_type,
        file_size_bytes=len(content),
        upload_status="processing",
    )
    db.add(contract)
    await db.flush()

    try:
        result = await process_contract_document(
            file_path=tmp_path,
            contract_id=contract_id,
            contract_type=contract_type,
            enable_vision=enable_vision,
        )
        contract.chunk_count = result["total_chunks"]
        contract.has_vision_processing = result["has_vision_processing"]
        contract.upload_status = "ready"
        await db.commit()

        duration = time.time() - start_time
        metrics.upload_completed(
            contract_type=contract_type,
            chunk_count=result["total_chunks"],
            pages_with_vision=result["pages_with_vision"],
            vision_tokens=result.get("vision_tokens_used", 0),
            duration_seconds=duration,
        )
        logger.info(
            "Contract uploaded",
            contract_id=contract_id,
            chunks=result["total_chunks"],
            vision_pages=result["pages_with_vision"],
            duration_s=round(duration, 2),
        )
        return ContractUploadResponse(
            contract_id=contract_id,
            filename=file.filename,
            total_chunks=result["total_chunks"],
            pages_with_vision=result["pages_with_vision"],
            has_vision_processing=result["has_vision_processing"],
            message="Contract processed and indexed successfully",
        )
    except Exception as e:
        contract.upload_status = "failed"
        await db.commit()
        metrics.upload_failed(contract_type, type(e).__name__)
        logger.error("Contract upload failed", error=str(e), contract_id=contract_id)
        raise HTTPException(500, "Document processing failed")
    finally:
        os.unlink(tmp_path)


# ─── Contract Review ──────────────────────────────────────────────────────────

@app.post("/api/contracts/review", response_model=ContractReviewResponse)
async def review_contract(
    request: ContractReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    result_contract = await db.execute(
        select(Contract).where(Contract.id == uuid.UUID(request.contract_id))
    )
    contract = result_contract.scalar_one_or_none()
    if not contract:
        raise HTTPException(404, "Contract not found")

    metrics.review_started(request.contract_type)

    # The contract's chunks are fetched with a metadata filter; the probe embedding only
    # satisfies the vector-search API and does not influence which chunks qualify.
    probe_embedding = await get_single_embedding(f"contract text {contract.original_filename}")
    hits = search_contracts(probe_embedding, top_k=50, filter_expr=contract_filter(request.contract_id))

    if not hits:
        raise HTTPException(400, "Contract text not indexed — please re-upload")

    chunks = sorted(
        [h.get("entity", {}) for h in hits],
        key=lambda x: x.get("chunk_index", 0),
    )
    full_text = "\n\n".join(c.get("text", "") for c in chunks)

    try:
        review_result = await run_full_contract_review(
            contract_text=full_text,
            contract_id=request.contract_id,
            contract_filename=contract.original_filename,
            contract_type=request.contract_type,
        )
    except Exception as e:
        metrics.review_failed(request.contract_type, type(e).__name__)
        logger.error("Contract review failed", contract_id=request.contract_id, error=str(e))
        raise HTTPException(500, "Contract review failed")

    review_id = str(uuid.uuid4())
    review = ContractReview(
        id=uuid.UUID(review_id),
        contract_id=uuid.UUID(request.contract_id),
        review_status=ReviewStatus.COMPLETED,
        overall_risk_score=review_result.get("overall_risk_score", 50),
        overall_risk_level=review_result.get("overall_risk_level", "medium"),
        total_clauses_found=review_result.get("total_clauses_found", 0),
        high_risk_clause_count=review_result.get("high_risk_count", 0),
        critical_clause_count=review_result.get("critical_count", 0),
        extractor_output=review_result.get("extractor_output"),
        risk_analyst_output=review_result.get("risk_analyst_output"),
        comparator_output=review_result.get("comparator_output"),
        synthesis_output=review_result.get("synthesis_output"),
        negotiation_priorities=review_result.get("negotiation_priorities"),
        review_duration_seconds=review_result.get("review_duration_seconds"),
        total_tokens_used=review_result.get("total_tokens_used", 0),
        total_cost_usd=review_result.get("total_cost_usd", 0),
        models_used=review_result.get("models_used"),
        completed_at=datetime.utcnow(),
    )
    db.add(review)

    for clause in review_result.get("all_clauses", [])[:100]:
        ec = ExtractedClause(
            contract_id=uuid.UUID(request.contract_id),
            clause_type=clause.get("clause_type", "general")[:200],
            clause_text=clause.get("clause_text", "")[:5000],
            risk_level=clause.get("risk_level", "low"),
            risk_reasoning=clause.get("risk_reasoning", ""),
            suggested_redline=clause.get("suggested_redline", ""),
            confidence_score=clause.get("confidence_score"),
        )
        db.add(ec)

    await db.commit()

    # Emit review metrics
    metrics.review_completed(
        contract_type=request.contract_type,
        risk_level=review_result.get("overall_risk_level", "medium"),
        duration_seconds=review_result.get("review_duration_seconds", 0),
        total_tokens=review_result.get("total_tokens_used", 0),
        cost_usd=review_result.get("total_cost_usd", 0),
        clause_count=review_result.get("total_clauses_found", 0),
        critical_count=review_result.get("critical_count", 0),
        high_count=review_result.get("high_risk_count", 0),
    )
    metrics.total_cost_recorded(review_result.get("total_cost_usd", 0), "review")

    logger.info(
        "Review completed",
        contract_id=request.contract_id,
        review_id=review_id,
        risk_level=review_result.get("overall_risk_level"),
        cost_usd=review_result.get("total_cost_usd"),
        duration_s=review_result.get("review_duration_seconds"),
    )

    return ContractReviewResponse(
        contract_id=request.contract_id,
        review_id=review_id,
        overall_risk_level=review_result.get("overall_risk_level", "medium"),
        overall_risk_score=review_result.get("overall_risk_score", 50),
        executive_summary=review_result.get("executive_summary", ""),
        total_clauses_found=review_result.get("total_clauses_found", 0),
        high_risk_count=review_result.get("high_risk_count", 0),
        critical_count=review_result.get("critical_count", 0),
        top_5_issues=review_result.get("top_5_issues", []),
        negotiation_priorities=review_result.get("negotiation_priorities", []),
        deal_breakers=review_result.get("deal_breakers", []),
        confidence_score=review_result.get("confidence_score", 70),
        review_duration_seconds=review_result.get("review_duration_seconds", 0),
        total_cost_usd=review_result.get("total_cost_usd", 0),
        models_used=review_result.get("models_used", []),
    )


# ─── Contract Search ──────────────────────────────────────────────────────────

@app.post("/api/contracts/search", response_model=SearchResponse)
async def search_contract_library(request: SearchRequest):
    start_ms = time.time() * 1000

    rewritten = await rewrite_query_for_search(request.query)
    query_embedding = await get_single_embedding(rewritten)

    # The semantic cache is keyed by query similarity only, so it is bypassed for
    # contract-scoped searches to avoid returning another contract's results.
    cached = check_semantic_cache(query_embedding) if not request.contract_id else None
    if cached:
        latency_ms = time.time() * 1000 - start_ms
        metrics.search_executed(cache_hit=True, top_k=request.top_k, result_count=len(cached.get("results", [])), latency_ms=latency_ms)
        metrics.cache_cost_saved(0.0003)
        return SearchResponse(
            query=request.query,
            rewritten_query=rewritten,
            results=cached.get("results", []),
            cache_hit=True,
            total_cost_usd=0.0,
        )

    filter_expr = contract_filter(request.contract_id) if request.contract_id else None
    hits = search_contracts(query_embedding, top_k=request.top_k * 2, filter_expr=filter_expr)
    reranked = rerank_chunks(rewritten, hits, top_k=request.top_k)

    results = []
    for hit in reranked:
        entity = hit.get("entity", hit)
        results.append({
            "text": entity.get("text", "")[:500],
            "contract_id": entity.get("contract_id", ""),
            "page_number": entity.get("page_number", 0),
            "has_vision_enrichment": entity.get("has_vision_enrichment", False),
            "relevance_score": hit.get("rerank_score", hit.get("distance", 0)),
        })

    if not request.contract_id:
        store_in_cache(
            cache_id=str(uuid.uuid4()).replace("-", "")[:32],
            query_embedding=query_embedding,
            query_text=rewritten,
            response={"results": results, "query": rewritten},
        )

    latency_ms = time.time() * 1000 - start_ms
    cost = 0.0003
    metrics.search_executed(cache_hit=False, top_k=request.top_k, result_count=len(results), latency_ms=latency_ms)
    metrics.total_cost_recorded(cost, "search")

    return SearchResponse(
        query=request.query,
        rewritten_query=rewritten,
        results=results,
        cache_hit=False,
        total_cost_usd=cost,
    )


# ─── Regulatory Monitoring ────────────────────────────────────────────────────

@app.post("/api/regulatory/check", response_model=RegulatoryCheckResponse)
async def trigger_regulatory_check(db: AsyncSession = Depends(get_db)):
    result = await run_regulatory_monitoring_cycle(db)
    logger.info("Regulatory check completed", **result)
    return RegulatoryCheckResponse(**result)


@app.get("/api/regulatory/changes")
async def get_regulatory_changes(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RegulatoryDocument).order_by(desc(RegulatoryDocument.created_at)).limit(limit)
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "source_name": d.source_name,
            "source_url": d.source_url,
            "change_summary": d.change_summary,
            "has_changes": d.has_changes_from_previous,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@app.get("/api/regulatory/impacts/{contract_id}")
async def get_contract_regulatory_impacts(contract_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RegulatoryImpact)
        .where(RegulatoryImpact.contract_id == _parse_uuid(contract_id))
        .order_by(desc(RegulatoryImpact.created_at))
    )
    impacts = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "impact_description": i.impact_description,
            "severity": i.severity.value if i.severity else "medium",
            "compliance_gap": i.compliance_gap,
            "recommended_action": i.recommended_action,
            "created_at": i.created_at.isoformat(),
        }
        for i in impacts
    ]


# ─── Contracts List ───────────────────────────────────────────────────────────

@app.get("/api/contracts")
async def list_contracts(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Contract).order_by(desc(Contract.created_at)).limit(limit)
    )
    contracts = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "filename": c.original_filename,
            "contract_type": c.contract_type,
            "chunk_count": c.chunk_count,
            "has_vision_processing": c.has_vision_processing,
            "upload_status": c.upload_status,
            "created_at": c.created_at.isoformat(),
        }
        for c in contracts
    ]


@app.get("/api/contracts/{contract_id}/reviews")
async def get_contract_reviews(contract_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ContractReview)
        .where(ContractReview.contract_id == _parse_uuid(contract_id))
        .order_by(desc(ContractReview.created_at))
        .limit(10)
    )
    reviews = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "review_status": r.review_status.value,
            "overall_risk_level": r.overall_risk_level.value if r.overall_risk_level else None,
            "overall_risk_score": r.overall_risk_score,
            "total_clauses_found": r.total_clauses_found,
            "high_risk_clause_count": r.high_risk_clause_count,
            "critical_clause_count": r.critical_clause_count,
            "synthesis_output": r.synthesis_output,
            "total_cost_usd": r.total_cost_usd,
            "models_used": r.models_used,
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


# ─── Evaluation ───────────────────────────────────────────────────────────────

@app.post("/api/evaluation/run")
async def run_evaluation(request: EvaluationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ContractReview)
        .where(ContractReview.review_status == ReviewStatus.COMPLETED)
        .order_by(desc(ContractReview.created_at))
        .limit(20)
    )
    reviews = result.scalars().all()
    if not reviews:
        raise HTTPException(400, "No completed reviews found to evaluate")

    review_results = []
    for r in reviews:
        review_results.append({
            "contract_id": str(r.contract_id),
            "all_clauses": r.risk_analyst_output.get("risk_assessments", []) if r.risk_analyst_output else [],
            "top_5_issues": r.synthesis_output.get("top_5_issues", []) if r.synthesis_output else [],
            "deal_breakers": r.synthesis_output.get("deal_breakers", []) if r.synthesis_output else [],
            "overall_risk_level": r.overall_risk_level.value if r.overall_risk_level else "medium",
            "overall_risk_score": r.overall_risk_score or 50,
            "negotiation_priorities": r.negotiation_priorities or [],
        })

    benchmark = run_benchmark_evaluation(review_results)

    eval_run = EvaluationRun(
        run_name=f"Evaluation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        total_contracts_evaluated=benchmark["total_contracts_evaluated"],
        correctness_score=benchmark["dimension_scores"]["correctness"],
        severity_calibration_score=benchmark["dimension_scores"]["severity_calibration"],
        completeness_score=benchmark["dimension_scores"]["completeness"],
        actionability_score=benchmark["dimension_scores"]["actionability"],
        overall_score=benchmark["overall_score"],
        results_detail=benchmark,
    )
    db.add(eval_run)
    await db.commit()

    # Emit judge scores
    metrics.judge_evaluation_completed(
        overall_score=benchmark["overall_score"],
        correctness=benchmark["dimension_scores"]["correctness"],
        severity_calibration=benchmark["dimension_scores"]["severity_calibration"],
        completeness=benchmark["dimension_scores"]["completeness"],
        actionability=benchmark["dimension_scores"]["actionability"],
        contracts_evaluated=benchmark["total_contracts_evaluated"],
    )
    logger.info("Evaluation completed", overall_score=benchmark["overall_score"], contracts=benchmark["total_contracts_evaluated"])
    return benchmark


@app.get("/api/evaluation/history")
async def get_evaluation_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EvaluationRun).order_by(desc(EvaluationRun.created_at)).limit(10)
    )
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "run_name": r.run_name,
            "total_contracts": r.total_contracts_evaluated,
            "overall_score": r.overall_score,
            "correctness": r.correctness_score,
            "severity_calibration": r.severity_calibration_score,
            "completeness": r.completeness_score,
            "actionability": r.actionability_score,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


# ─── Red-Teaming ──────────────────────────────────────────────────────────────

@app.post("/api/redteam/run")
async def run_red_team(request: RedTeamRequest, db: AsyncSession = Depends(get_db)):
    result = await run_red_team_evaluation(
        review_function=run_full_contract_review,
        iteration=request.iteration,
    )
    patches = generate_patch_recommendations(result)

    run = RedTeamRun(
        run_name=f"Red Team Iteration {request.iteration} — {datetime.utcnow().strftime('%Y-%m-%d')}",
        iteration_number=request.iteration,
        total_adversarial_contracts=result["total_adversarial_contracts"],
        failure_rate_after=result["failure_rate"],
        attack_category_results=result["category_breakdown"],
        patches_applied=patches,
    )
    db.add(run)
    await db.commit()

    # Emit red-team metrics
    metrics.red_team_run_completed(
        iteration=request.iteration,
        total_contracts=result["total_adversarial_contracts"],
        failure_rate=result["failure_rate"],
        category_results=result.get("category_breakdown", {}),
    )
    logger.info(
        "Red-team run completed",
        iteration=request.iteration,
        failure_rate=result["failure_rate"],
        contracts=result["total_adversarial_contracts"],
    )
    return {**result, "patch_recommendations": patches}


@app.get("/api/redteam/history")
async def get_redteam_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RedTeamRun).order_by(desc(RedTeamRun.created_at)).limit(10)
    )
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "run_name": r.run_name,
            "iteration": r.iteration_number,
            "total_contracts": r.total_adversarial_contracts,
            "failure_rate": r.failure_rate_after,
            "attack_categories": r.attack_category_results,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(Contract.id)))
    total_contracts = result.scalar()

    result = await db.execute(select(func.count(ContractReview.id)))
    total_reviews = result.scalar()

    result = await db.execute(
        select(ContractReview.overall_risk_level, func.count(ContractReview.id))
        .where(ContractReview.overall_risk_level.isnot(None))
        .group_by(ContractReview.overall_risk_level)
    )
    risk_dist = dict(result.all())

    result = await db.execute(select(func.sum(ContractReview.total_cost_usd)))
    total_cost = result.scalar() or 0.0

    result = await db.execute(select(func.count(RegulatoryDocument.id)))
    reg_changes = result.scalar()

    # Publish current gauges
    from backend.core.datadog_setup import statsd as dd_statsd
    dd_statsd.gauge("legal_intel.stats.total_contracts", total_contracts or 0)
    dd_statsd.gauge("legal_intel.stats.total_reviews", total_reviews or 0)
    dd_statsd.gauge("legal_intel.stats.total_cost_usd", round(total_cost, 4))
    dd_statsd.gauge("legal_intel.stats.regulatory_changes", reg_changes or 0)

    return {
        "total_contracts": total_contracts,
        "total_reviews": total_reviews,
        "risk_distribution": {k.value if hasattr(k, "value") else k: v for k, v in risk_dist.items()},
        "total_cost_usd": round(total_cost, 4),
        "regulatory_changes": reg_changes,
        "timestamp": datetime.utcnow().isoformat(),
    }
