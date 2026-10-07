# Security

## Secrets and configuration

- All credentials are read from environment variables. `.env` is git-ignored; `.env.example` contains placeholders only.
- Compose requires `POSTGRES_PASSWORD` explicitly; there is no default database password.
- The Compose PostgreSQL port is bound to `127.0.0.1`.

## Input handling

- Request bodies are validated with Pydantic. Contract identifiers are parsed as UUIDs before use in SQL queries and in Milvus filter expressions (`contract_filter`), which prevents filter-expression injection.
- Uploads are limited to `.pdf`, `.docx` and `.txt` and to `MAX_UPLOAD_MB` (default 25). Temporary files are deleted after processing.
- Upload and review failures return generic error messages; details are logged.
- The semantic cache is not used for contract-scoped searches, so cached results from one contract cannot be returned for another.

## Data exposure to third parties

Contract text is sent to the configured model providers (Anthropic, OpenAI, Google, Groq), to Cohere for reranking, and to Milvus / Zilliz Cloud for storage. Confirm that provider agreements and data-processing terms meet your obligations before processing confidential documents.

Datadog LLM spans record model, provider, tokens, cost and latency by default. Prompt and response excerpts are attached only when `DD_CAPTURE_LLM_CONTENT=true`.

## Container hardening

Application images run as a non-root user. The backend image exposes a health check on `/health`.

## Known limitations and recommended controls

| Area | Current state | Recommended control |
|---|---|---|
| Authentication / authorisation | None in the application | Deploy behind an authenticating gateway or private network; add per-tenant access control before multi-user use |
| CORS | `*` by default for local development | Set `CORS_ORIGINS` to explicit origins in any shared environment |
| Rate limiting | None | Apply at the gateway; model calls are billable |
| Data retention | Contracts, chunks and reviews persist until deleted | Define retention and deletion policy; `delete_contract_chunks` exists for vector cleanup |
| Audit trail | `governance_records` table exists but is not exposed via API | Add approval workflow endpoints before relying on it |
| Regulatory fetching | Fetches configured URLs only | Restrict `REGULATORY_SOURCES` to trusted hosts |

## Reporting

Report suspected vulnerabilities privately to the repository owner rather than through public issues.
