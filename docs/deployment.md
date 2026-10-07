# Deployment

## Prerequisites

- Python 3.11 (or Docker)
- PostgreSQL 14+
- A Milvus instance (Zilliz Cloud URI and API key)
- API keys for Anthropic, OpenAI, Google, Groq and Cohere
- Optional: a Datadog account and Agent

## Docker Compose

```bash
cp .env.example .env
# set POSTGRES_PASSWORD, provider keys, ZILLIZ_CLOUD_URI and ZILLIZ_CLOUD_API_KEY
docker compose up --build
```

Services: `backend` (8000), `frontend` (8501), `postgres` (localhost only). Compose overrides `DATABASE_URL` and `BACKEND_URL` for the container network. Datadog tracing is disabled by default in Compose.

With Datadog:

```bash
# in .env: DD_API_KEY=..., DD_AGENT_HOST=datadog-agent, DD_TRACE_ENABLED=true
docker compose --profile observability up --build
```

Import `infrastructure/observability/datadog-dashboard.json` through Datadog's dashboard import.

## Database migrations

```bash
alembic upgrade head
```

Alembic reads `DATABASE_URL_SYNC` (derived from `DATABASE_URL` when empty). The API also creates missing tables at startup, which is convenient for first runs; use migrations in managed environments.

## Render

`render.yaml` defines the API web service (health check `/health`, started with `ddtrace-run`) and a PostgreSQL instance. Secret values are marked `sync: false` and must be set in the Render dashboard. Render supplies `postgres://` connection strings; the application normalises them for asyncpg. Set `CORS_ORIGINS` to the UI origin, and set `DD_AGENT_HOST` to a reachable Datadog Agent or `DD_TRACE_ENABLED=false`.

The Streamlit UI can be deployed as a second service using `infrastructure/docker/Dockerfile.frontend` with `BACKEND_URL` set to the API URL.

## MCP servers

The servers run over stdio and are launched by the MCP client. Example client configuration (adjust the path and Python executable):

```json
{
  "mcpServers": {
    "legal-contracts":  { "command": "python", "args": ["-m", "backend.mcp_servers.contract_intelligence_mcp"],   "cwd": "/path/to/legal-intelligence-agent" },
    "legal-regulatory": { "command": "python", "args": ["-m", "backend.mcp_servers.regulatory_intelligence_mcp"], "cwd": "/path/to/legal-intelligence-agent" },
    "legal-search":     { "command": "python", "args": ["-m", "backend.mcp_servers.legal_document_search_mcp"],    "cwd": "/path/to/legal-intelligence-agent" },
    "legal-risk":       { "command": "python", "args": ["-m", "backend.mcp_servers.risk_evaluation_mcp"],          "cwd": "/path/to/legal-intelligence-agent" }
  }
}
```

The servers read the same `.env` as the API (from `cwd`) and need the same provider, Milvus and database settings.

| Server | Tools |
|---|---|
| `legal-contracts` | `review_contract`, `extract_clauses`, `flag_risky_clauses`, `compare_to_template`, `generate_redline_suggestions`, `get_negotiation_priorities` |
| `legal-regulatory` | `get_recent_regulatory_changes`, `check_contract_compliance`, `get_affected_contracts`, `subscribe_to_regulatory_source`, `get_compliance_report` |
| `legal-search` | `search_contract_library`, `find_similar_clauses`, `get_clause_history` |
| `legal-risk` | `score_contract_risk`, `classify_clause_severity`, `get_negotiation_priorities` |

## Scheduling regulatory checks

The API does not schedule checks itself. Call `POST /api/regulatory/check` from your scheduler (cron, Render cron job, Kubernetes CronJob).
