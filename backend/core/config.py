"""Application settings, loaded from environment variables (and an optional local ``.env``)."""
import re
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_async_database_url(url: str) -> str:
    """Return a SQLAlchemy asyncpg URL.

    Managed Postgres providers hand out ``postgres://`` / ``postgresql://`` URLs with a
    libpq-style ``sslmode`` parameter. asyncpg expects the ``postgresql+asyncpg`` driver and
    ``ssl`` instead, so both are translated here.
    """
    if not url:
        return url
    url = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql+asyncpg://", url)
    return re.sub(r"([?&])sslmode=", r"\1ssl=", url)


def normalize_sync_database_url(url: str) -> str:
    """Return a synchronous (psycopg2) URL suitable for Alembic."""
    if not url:
        return url
    url = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql://", url)
    return re.sub(r"([?&])ssl=", r"\1sslmode=", url)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_env: str = "development"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    # Comma-separated list of allowed browser origins for CORS ("*" allows any origin).
    cors_origins: str = "*"
    # Maximum accepted upload size in megabytes.
    max_upload_mb: int = 25

    # AI providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    cohere_api_key: str = ""

    # Vector database (Milvus / Zilliz Cloud)
    zilliz_cloud_uri: str = ""
    zilliz_cloud_api_key: str = ""

    # Relational database. ``database_url_sync`` is derived from ``database_url`` when omitted.
    database_url: str = ""
    database_url_sync: str = ""

    # Observability: Datadog (APM, DogStatsD metrics, log correlation)
    dd_api_key: str = ""
    dd_site: str = "datadoghq.com"
    dd_service: str = "legal-intel-agent"
    dd_env: str = ""  # falls back to app_env when empty
    dd_agent_host: str = "localhost"  # "datadog-agent" inside Docker Compose
    dd_agent_port: int = 8126  # APM trace receiver
    dd_dogstatsd_port: int = 8125  # DogStatsD metrics
    dd_log_level: str = "WARN"
    dd_trace_enabled: bool = True
    # Attach prompt/response excerpts to LLM spans. Off by default: contract text is
    # confidential and should not leave the deployment unless explicitly enabled.
    dd_capture_llm_content: bool = False

    # Feature flags
    enable_vision_processing: bool = True

    # Milvus collection names
    contracts_collection: str = "legal_contracts"
    regulatory_collection: str = "regulatory_documents"
    cache_collection: str = "semantic_cache"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Retrieval
    retrieval_top_k: int = 10
    rerank_top_k: int = 5
    cache_similarity_threshold: float = 0.92

    # Regulatory monitoring: comma-separated source URLs
    regulatory_sources: str = ""

    @model_validator(mode="after")
    def _normalize_database_urls(self) -> "Settings":
        if self.database_url:
            if not self.database_url_sync:
                self.database_url_sync = self.database_url
            self.database_url = normalize_async_database_url(self.database_url)
        if self.database_url_sync:
            self.database_url_sync = normalize_sync_database_url(self.database_url_sync)
        return self

    @property
    def regulatory_source_list(self) -> List[str]:
        if not self.regulatory_sources:
            return []
        return [s.strip() for s in self.regulatory_sources.split(",") if s.strip()]

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]

    @property
    def effective_dd_env(self) -> str:
        """Use explicit DD_ENV if set, otherwise fall back to APP_ENV."""
        return self.dd_env if self.dd_env else self.app_env


settings = Settings()
