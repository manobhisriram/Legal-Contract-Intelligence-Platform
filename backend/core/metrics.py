"""
backend/core/metrics.py

Every custom metric this system emits is defined here.
One place to see all metric names, tags, and what they measure.
Import this module wherever metrics need to be recorded.

Metric naming convention: legal_intel.<subsystem>.<measurement>
Tags always include relevant context (model, risk_level, contract_type, etc.)

Datadog metric types used:
- INCREMENT  : counting events (reviews started, errors, cache hits)
- HISTOGRAM  : measuring distributions (token counts, latency, cost per call)
- GAUGE      : current state (queue depth, active contracts, cache size)
- DISTRIBUTION: percentile-accurate distributions (p50/p95/p99 in Datadog)
"""

from backend.core.datadog_setup import statsd


# ─── Contract Review Metrics ──────────────────────────────────────────────────

def review_started(contract_type: str = "general"):
    statsd.increment(
        "legal_intel.review.started",
        tags=[f"contract_type:{contract_type}"],
    )


def review_completed(
    contract_type: str,
    risk_level: str,
    duration_seconds: float,
    total_tokens: int,
    cost_usd: float,
    clause_count: int,
    critical_count: int,
    high_count: int,
):
    tags = [
        f"contract_type:{contract_type}",
        f"risk_level:{risk_level}",
    ]
    statsd.increment("legal_intel.review.completed", tags=tags)
    statsd.distribution("legal_intel.review.duration_seconds", duration_seconds, tags=tags)
    statsd.distribution("legal_intel.review.total_tokens", total_tokens, tags=tags)
    statsd.distribution("legal_intel.review.cost_usd", cost_usd, tags=tags)
    statsd.histogram("legal_intel.review.clause_count", clause_count, tags=tags)
    statsd.histogram("legal_intel.review.critical_clauses", critical_count, tags=tags)
    statsd.histogram("legal_intel.review.high_risk_clauses", high_count, tags=tags)
    # Risk level distribution
    statsd.increment(f"legal_intel.review.risk.{risk_level}", tags=[f"contract_type:{contract_type}"])


def review_failed(contract_type: str = "general", error_type: str = "unknown"):
    statsd.increment(
        "legal_intel.review.failed",
        tags=[f"contract_type:{contract_type}", f"error_type:{error_type}"],
    )


# ─── Agent-Level Metrics ──────────────────────────────────────────────────────

def agent_call(
    agent_name: str,
    model: str,
    provider: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: float,
    success: bool = True,
):
    tags = [
        f"agent:{agent_name}",
        f"model:{model}",
        f"provider:{provider}",
        f"success:{success}",
    ]
    statsd.increment("legal_intel.agent.calls", tags=tags)
    statsd.distribution("legal_intel.agent.latency_ms", latency_ms, tags=tags)
    statsd.distribution("legal_intel.agent.tokens.input", input_tokens, tags=tags)
    statsd.distribution("legal_intel.agent.tokens.output", output_tokens, tags=tags)
    statsd.distribution("legal_intel.agent.cost_usd", cost_usd, tags=tags)
    if not success:
        statsd.increment("legal_intel.agent.errors", tags=tags)


# ─── Document Upload Metrics ──────────────────────────────────────────────────

def upload_started(contract_type: str, vision_enabled: bool):
    statsd.increment(
        "legal_intel.upload.started",
        tags=[f"contract_type:{contract_type}", f"vision:{vision_enabled}"],
    )


def upload_completed(
    contract_type: str,
    chunk_count: int,
    pages_with_vision: int,
    vision_tokens: int,
    duration_seconds: float,
):
    tags = [f"contract_type:{contract_type}"]
    statsd.increment("legal_intel.upload.completed", tags=tags)
    statsd.histogram("legal_intel.upload.chunk_count", chunk_count, tags=tags)
    statsd.histogram("legal_intel.upload.vision_pages", pages_with_vision, tags=tags)
    if vision_tokens > 0:
        statsd.distribution("legal_intel.upload.vision_tokens", vision_tokens, tags=tags)
    statsd.distribution("legal_intel.upload.duration_seconds", duration_seconds, tags=tags)


def upload_failed(contract_type: str, error_type: str):
    statsd.increment(
        "legal_intel.upload.failed",
        tags=[f"contract_type:{contract_type}", f"error_type:{error_type}"],
    )


# ─── Vision Processing Metrics ────────────────────────────────────────────────

def vision_page_processed(provider: str, had_visual_content: bool, tokens_used: int):
    tags = [f"provider:{provider}", f"had_visuals:{had_visual_content}"]
    statsd.increment("legal_intel.vision.pages_processed", tags=tags)
    if tokens_used > 0:
        statsd.distribution("legal_intel.vision.tokens", tokens_used, tags=tags)


def vision_fallback_triggered(reason: str):
    statsd.increment(
        "legal_intel.vision.fallback_triggered",
        tags=[f"reason:{reason}"],
    )


# ─── Search & Retrieval Metrics ───────────────────────────────────────────────

def search_executed(cache_hit: bool, top_k: int, result_count: int, latency_ms: float):
    tags = [f"cache_hit:{cache_hit}"]
    statsd.increment("legal_intel.search.executed", tags=tags)
    statsd.distribution("legal_intel.search.latency_ms", latency_ms, tags=tags)
    statsd.histogram("legal_intel.search.result_count", result_count, tags=tags)
    if cache_hit:
        statsd.increment("legal_intel.search.cache_hits")
    else:
        statsd.increment("legal_intel.search.cache_misses")


def rerank_executed(input_count: int, output_count: int, latency_ms: float):
    statsd.increment("legal_intel.rerank.executed")
    statsd.distribution("legal_intel.rerank.latency_ms", latency_ms, tags=[])
    statsd.histogram("legal_intel.rerank.input_count", input_count)
    statsd.histogram("legal_intel.rerank.output_count", output_count)


def embedding_batch_executed(batch_size: int, latency_ms: float, success: bool = True):
    tags = [f"success:{success}"]
    statsd.increment("legal_intel.embedding.batches", tags=tags)
    statsd.histogram("legal_intel.embedding.batch_size", batch_size, tags=tags)
    statsd.distribution("legal_intel.embedding.latency_ms", latency_ms, tags=tags)


# ─── Regulatory Monitoring Metrics ───────────────────────────────────────────

def regulatory_check_completed(
    source_name: str,
    changed: bool,
    contracts_impacted: int,
    duration_seconds: float,
):
    tags = [f"source:{source_name}", f"changed:{changed}"]
    statsd.increment("legal_intel.regulatory.checks", tags=tags)
    statsd.distribution("legal_intel.regulatory.check_duration_seconds", duration_seconds, tags=tags)
    if changed:
        statsd.increment("legal_intel.regulatory.changes_detected", tags=[f"source:{source_name}"])
        statsd.histogram(
            "legal_intel.regulatory.contracts_impacted",
            contracts_impacted,
            tags=[f"source:{source_name}"],
        )


def regulatory_check_failed(source_name: str, error_type: str):
    statsd.increment(
        "legal_intel.regulatory.check_failed",
        tags=[f"source:{source_name}", f"error:{error_type}"],
    )


# ─── LLM Judge Evaluation Metrics ────────────────────────────────────────────

def judge_evaluation_completed(
    overall_score: float,
    correctness: float,
    severity_calibration: float,
    completeness: float,
    actionability: float,
    contracts_evaluated: int,
):
    statsd.gauge("legal_intel.judge.overall_score", overall_score * 100)
    statsd.gauge("legal_intel.judge.correctness_score", correctness * 100)
    statsd.gauge("legal_intel.judge.severity_calibration_score", severity_calibration * 100)
    statsd.gauge("legal_intel.judge.completeness_score", completeness * 100)
    statsd.gauge("legal_intel.judge.actionability_score", actionability * 100)
    statsd.histogram("legal_intel.judge.contracts_evaluated", contracts_evaluated)
    statsd.increment("legal_intel.judge.evaluation_runs")


# ─── Red-Team Metrics ─────────────────────────────────────────────────────────

def red_team_run_completed(
    iteration: int,
    total_contracts: int,
    failure_rate: float,
    category_results: dict,
):
    tags = [f"iteration:{iteration}"]
    statsd.gauge("legal_intel.redteam.failure_rate", failure_rate * 100, tags=tags)
    statsd.gauge("legal_intel.redteam.success_rate", (1 - failure_rate) * 100, tags=tags)
    statsd.histogram("legal_intel.redteam.contracts_tested", total_contracts, tags=tags)
    statsd.increment("legal_intel.redteam.runs_completed", tags=tags)
    # Per-category failure rates
    for category, data in category_results.items():
        cat_tags = tags + [f"category:{category}"]
        statsd.gauge(
            "legal_intel.redteam.category_failure_rate",
            data.get("failure_rate", 0) * 100,
            tags=cat_tags,
        )


# ─── Milvus / Vector DB Metrics ───────────────────────────────────────────────

def milvus_search_executed(collection: str, top_k: int, latency_ms: float, result_count: int):
    tags = [f"collection:{collection}"]
    statsd.increment("legal_intel.milvus.searches", tags=tags)
    statsd.distribution("legal_intel.milvus.search_latency_ms", latency_ms, tags=tags)
    statsd.histogram("legal_intel.milvus.top_k", top_k, tags=tags)
    statsd.histogram("legal_intel.milvus.result_count", result_count, tags=tags)


def milvus_upsert_executed(collection: str, record_count: int, latency_ms: float):
    tags = [f"collection:{collection}"]
    statsd.increment("legal_intel.milvus.upserts", tags=tags)
    statsd.histogram("legal_intel.milvus.upsert_record_count", record_count, tags=tags)
    statsd.distribution("legal_intel.milvus.upsert_latency_ms", latency_ms, tags=tags)


def milvus_cache_checked(hit: bool, similarity_score: float = 0.0):
    if hit:
        statsd.increment("legal_intel.milvus.cache_hits")
        statsd.distribution("legal_intel.milvus.cache_hit_similarity", similarity_score)
    else:
        statsd.increment("legal_intel.milvus.cache_misses")


# ─── MCP Server Metrics ───────────────────────────────────────────────────────

def mcp_tool_called(server_name: str, tool_name: str, success: bool, latency_ms: float):
    tags = [f"server:{server_name}", f"tool:{tool_name}", f"success:{success}"]
    statsd.increment("legal_intel.mcp.tool_calls", tags=tags)
    statsd.distribution("legal_intel.mcp.tool_latency_ms", latency_ms, tags=tags)
    if not success:
        statsd.increment("legal_intel.mcp.tool_errors", tags=tags)


# ─── API Endpoint Metrics ─────────────────────────────────────────────────────

def api_request_completed(endpoint: str, method: str, status_code: int, latency_ms: float):
    tags = [
        f"endpoint:{endpoint}",
        f"method:{method}",
        f"status:{status_code}",
        f"success:{status_code < 400}",
    ]
    statsd.increment("legal_intel.api.requests", tags=tags)
    statsd.distribution("legal_intel.api.latency_ms", latency_ms, tags=tags)
    if status_code >= 500:
        statsd.increment("legal_intel.api.errors_5xx", tags=tags)
    elif status_code >= 400:
        statsd.increment("legal_intel.api.errors_4xx", tags=tags)


# ─── Cost Aggregation Metrics ─────────────────────────────────────────────────

def total_cost_recorded(cost_usd: float, feature: str = "review"):
    """Record cumulative cost for FinOps tracking."""
    statsd.distribution(
        "legal_intel.cost.usd",
        cost_usd,
        tags=[f"feature:{feature}"],
    )


def cache_cost_saved(cost_usd: float):
    """Record how much a cache hit saved vs a full API call."""
    statsd.distribution("legal_intel.cost.cache_savings_usd", cost_usd)
