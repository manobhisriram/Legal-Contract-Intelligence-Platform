# Architecture

This document is for engineers working on the codebase. For a product-level overview see the [README](../README.md).

## Components

| Component | Location | Role |
|---|---|---|
| API | `backend/api/main.py` | FastAPI app: upload, review, search, regulatory, evaluation, red-team, dashboard endpoints; request-metrics middleware |
| Review pipeline | `backend/agents/contract_review_agent.py` | Four sequential agent functions plus the orchestrating `run_full_contract_review` |
| Regulatory agent | `backend/agents/regulatory_agent.py` | Source fetch and hashing, change summary, contract impact mapping |
| LLM judge | `backend/agents/llm_judge.py` | Four-dimension scoring of review results |
| Red-team suite | `backend/agents/red_team_agent.py` | 50 adversarial contracts, detection checks, prompt patch recommendations |
| Document service | `backend/services/document_service.py` | Text extraction (PDF, DOCX, TXT), page vision, chunk enrichment, indexing |
| Embedding service | `backend/services/embedding_service.py` | Batched embeddings, Cohere rerank, Groq query rewriting |
| Persistence | `backend/db/` | SQLAlchemy models and sessions; Milvus client and collections |
| MCP servers | `backend/mcp_servers/` | Four stdio servers calling the same backend modules directly |
| Core | `backend/core/` | Settings, structured logging, metrics catalogue, Datadog setup and `LLMSpan` |
| UI | `frontend/app.py` | Streamlit console calling the REST API |

## Request flows

### Upload and indexing

1. `POST /api/contracts/upload` validates extension (`.pdf`, `.docx`, `.txt`) and size, writes a temporary file and creates a `contracts` row (`processing`).
2. `extract_text` dispatches on extension. PDFs use `unstructured` (`hi_res`, table structure inference, title-based chunking) with a `pypdf` fallback.
3. For PDFs with vision enabled, up to 20 pages are rasterised and analysed by Claude; GPT-4o is the fallback on error. Pages with visual content have the vision text appended to their chunks (`has_vision_enrichment`).
4. Chunks are embedded in batches and upserted into the Milvus contracts collection.
5. The `contracts` row is updated (`ready` or `failed`) and the temporary file is removed.

### Contract review

1. `POST /api/contracts/review` loads the contract's chunks from Milvus (metadata-filtered, ordered by `chunk_index`) and joins them into the contract text.
2. The pipeline runs Extractor → Risk Analyst → Comparator → Synthesis. Risk results are merged back into the extracted clauses by position.
3. The API stores a `contract_reviews` row (all four stage outputs as JSON, risk level and score, token and cost totals, models used) and up to 100 `extracted_clauses` rows, then emits metrics.

### Search

1. The query is rewritten (Groq) and embedded (OpenAI).
2. Library-wide queries check the Milvus semantic cache; a hit above the similarity threshold returns the cached results. Contract-scoped queries skip the cache.
3. On a miss, Milvus returns `2 × top_k` candidates, Cohere reranks them, and library-wide results are written back to the cache.

### Regulatory monitoring

1. `POST /api/regulatory/check` iterates `REGULATORY_SOURCES`.
2. Each source is fetched and SHA-256 hashed and compared with the latest `regulatory_documents` row.
3. Changed (or new) sources are stored, summarised (for changes), chunked, embedded and indexed in the regulatory collection.
4. The change summary is embedded and matched against the contracts collection; for up to 10 matched contracts an impact assessment is generated and stored in `regulatory_impacts` with a keyword-derived severity.

### Evaluation

- `POST /api/evaluation/run` scores the 20 most recent completed reviews with the judge and stores an `evaluation_runs` row.
- `POST /api/redteam/run` pushes the adversarial contracts through the review pipeline, computes failure rates per category, stores a `red_team_runs` row and returns prompt-patch recommendations.

## Data model

PostgreSQL tables: `contracts`, `extracted_clauses`, `contract_reviews`, `regulatory_documents`, `regulatory_impacts`, `governance_records`, `evaluation_runs`, `red_team_runs`. Migrations live in `alembic/versions/`. The API also calls `create_all` at startup for first-run convenience; Alembic is the source of truth for managed environments.

Milvus collections (names configurable): `legal_contracts` (chunk text, page, vision flag, clause type, document type), `regulatory_documents`, `semantic_cache`. All use 1,536-dimension vectors with cosine similarity.

## Deployment topology

```text
Browser ──► Streamlit (8501) ──► FastAPI (8000) ──► PostgreSQL
                                      │
                                      ├──► Milvus / Zilliz Cloud
                                      ├──► Model providers (Anthropic, OpenAI, Google, Groq, Cohere)
                                      └──► Datadog Agent (APM 8126, DogStatsD 8125)

MCP client ──stdio──► MCP server processes ──► same backend modules, Milvus, PostgreSQL
```

The MCP servers are separate processes started by the MCP client; they do not call the REST API.

## Observability

- **Tracing:** `ddtrace` instruments FastAPI, SQLAlchemy and HTTP clients. `LLMSpan` wraps each agent call with provider, model, role, token and cost tags.
- **Metrics:** every metric name is declared in `backend/core/metrics.py` (`legal_intel.<subsystem>.<measurement>`), covering reviews, agents, uploads, vision, search and cache, embeddings, Milvus, regulatory checks, judge and red-team results, MCP calls, API latency and cost.
- **Logging:** `structlog` JSON to stdout with Datadog trace and span IDs injected when a span is active.
- **Dashboard:** `infrastructure/observability/datadog-dashboard.json` defines eight widget groups (business overview, APM, per-agent LLM metrics, Milvus, quality gates, regulatory, cost, risk distribution).
- **Fallbacks:** if Datadog libraries or the agent are unavailable, metrics fall back to a no-op client and the application continues to run.
