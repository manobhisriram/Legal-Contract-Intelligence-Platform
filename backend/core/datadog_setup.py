"""
backend/core/datadog_setup.py

Central Datadog initialisation for the Legal Intelligence Agent.
This module must be imported BEFORE any other backend module in main.py
so that ddtrace patches all libraries (FastAPI, SQLAlchemy, httpx, etc.)
at import time.

What this configures:
- APM: auto-instrumented traces for every HTTP request, DB query, HTTP client call
- LLM Observability: custom spans wrapping each of the 4 agents
- Custom Metrics: DogStatsD client for business + AI metrics
- Log injection: DD trace/span IDs injected into every structlog JSON line
- Runtime metrics: CPU, memory, thread counts from the Python process
"""

import os
import logging

# ─── ddtrace APM & LLM Observability ─────────────────────────────────────────

def init_datadog_apm():
    """
    Patch all supported libraries with ddtrace.
    Must be called before importing FastAPI, SQLAlchemy, httpx, anthropic, openai.
    In production (Render / Docker) the ddtrace-run launcher handles this automatically.
    In development (uvicorn direct) we call patch_all() manually here.
    """
    try:
        from ddtrace import patch_all, tracer, config as dd_config
        from backend.core.config import settings

        # Core tracer configuration
        tracer.configure(
            hostname=settings.dd_agent_host,
            port=settings.dd_agent_port,
        )

        # Service metadata — shows up in every trace in Datadog UI
        os.environ.setdefault("DD_SERVICE", settings.dd_service)
        os.environ.setdefault("DD_ENV", settings.app_env)
        os.environ.setdefault("DD_VERSION", settings.app_version)
        os.environ.setdefault("DD_TRACE_SAMPLE_RATE", "1.0")  # full sampling; lower in high-volume deployments
        os.environ.setdefault("DD_LOGS_INJECTION", "true")    # inject trace IDs into logs
        os.environ.setdefault("DD_RUNTIME_METRICS_ENABLED", "true")  # CPU/mem/threads

        # Patch all supported integrations automatically:
        # fastapi, starlette, sqlalchemy, asyncpg, httpx, requests, logging, grpc
        patch_all(logging=True)

        # FastAPI-specific: capture request body for debugging (disable in strict prod)
        dd_config.fastapi["request_span_name"] = "legal_intel.http.request"
        dd_config.fastapi["service_name"] = settings.dd_service

        # SQLAlchemy: capture query text (obfuscated by default)
        dd_config.sqlalchemy["service_name"] = f"{settings.dd_service}-postgres"
        dd_config.sqlalchemy["trace_fetch_methods"] = True

        return True
    except ImportError:
        logging.getLogger(__name__).warning(
            "ddtrace not installed — Datadog APM disabled. "
            "Run: pip install ddtrace datadog"
        )
        return False
    except Exception as e:
        logging.getLogger(__name__).error(f"Datadog APM init failed: {e}")
        return False


# ─── DogStatsD Custom Metrics Client ─────────────────────────────────────────

class _NoOpStatsd:
    """Silent no-op when Datadog is not available — app still works."""
    def increment(self, *a, **kw): pass
    def gauge(self, *a, **kw): pass
    def histogram(self, *a, **kw): pass
    def timing(self, *a, **kw): pass
    def distribution(self, *a, **kw): pass
    def event(self, *a, **kw): pass


def get_statsd():
    """
    Return a DogStatsD client connected to the Datadog Agent.
    Falls back to a no-op client if the datadog package is not installed
    or the agent is unreachable — the app continues to function.
    """
    try:
        from datadog import initialize, statsd
        from backend.core.config import settings

        # DD_TRACE_ENABLED=false turns off all Datadog emission (traces and DogStatsD metrics).
        if not settings.dd_trace_enabled:
            return _NoOpStatsd()

        initialize(
            statsd_host=settings.dd_agent_host,
            statsd_port=settings.dd_dogstatsd_port,
        )
        return statsd
    except ImportError:
        return _NoOpStatsd()
    except Exception:
        return _NoOpStatsd()


# Module-level singleton — imported everywhere via `from backend.core.datadog_setup import statsd`
statsd = get_statsd()


# ─── LLM Observability Span Context Manager ──────────────────────────────────

def _capture_content_enabled() -> bool:
    try:
        from backend.core.config import settings
        return settings.dd_capture_llm_content
    except Exception:
        return False


class LLMSpan:
    """
    Context manager that wraps a single LLM call with a Datadog APM span
    and records model, provider, token counts, cost, and error status.

    Usage:
        with LLMSpan("extractor_agent", model="claude-sonnet-4-5", provider="anthropic") as span:
            result = call_claude(...)
            span.set_tokens(input_tokens=800, output_tokens=300)
            span.set_cost(0.0021)
    """

    def __init__(
        self,
        operation_name: str,
        model: str = "",
        provider: str = "",
        agent_role: str = "",
    ):
        self.operation_name = operation_name
        self.model = model
        self.provider = provider
        self.agent_role = agent_role
        self._span = None
        self._input_tokens = 0
        self._output_tokens = 0
        self._cost = 0.0
        self._error = None

    def __enter__(self):
        try:
            from ddtrace import tracer
            self._span = tracer.start_span(
                f"llm.{self.operation_name}",
                resource=self.model,
            )
            # LLM Observability standard tags
            self._span.set_tag("llm.provider", self.provider)
            self._span.set_tag("llm.model", self.model)
            self._span.set_tag("llm.agent_role", self.agent_role)
            self._span.set_tag("span.kind", "llm")
        except Exception:
            pass
        return self

    def set_tokens(self, input_tokens: int = 0, output_tokens: int = 0):
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        if self._span:
            try:
                self._span.set_metric("llm.usage.input_tokens", input_tokens)
                self._span.set_metric("llm.usage.output_tokens", output_tokens)
                self._span.set_metric("llm.usage.total_tokens", input_tokens + output_tokens)
            except Exception:
                pass

    def set_cost(self, cost_usd: float):
        self._cost = cost_usd
        if self._span:
            try:
                self._span.set_metric("llm.usage.cost_usd", cost_usd)
            except Exception:
                pass

    def set_input(self, prompt: str):
        if self._span and _capture_content_enabled():
            try:
                # Store first 1000 chars of prompt for debugging
                self._span.set_tag("llm.request.prompt", prompt[:1000])
            except Exception:
                pass

    def set_output(self, response: str):
        if self._span and _capture_content_enabled():
            try:
                self._span.set_tag("llm.response.text", response[:500])
            except Exception:
                pass

    def set_error(self, error: Exception):
        self._error = error
        if self._span:
            try:
                self._span.set_tag("error", True)
                self._span.set_tag("error.message", str(error))
                self._span.set_tag("error.type", type(error).__name__)
            except Exception:
                pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val and self._span:
            self.set_error(exc_val)
        if self._span:
            try:
                self._span.finish()
            except Exception:
                pass

        # Always emit StatsD metrics regardless of span success
        tags = [
            f"model:{self.model}",
            f"provider:{self.provider}",
            f"agent:{self.agent_role}",
            f"operation:{self.operation_name}",
        ]
        statsd.increment("legal_intel.llm.calls", tags=tags)
        if self._input_tokens or self._output_tokens:
            statsd.histogram(
                "legal_intel.llm.tokens.input",
                self._input_tokens,
                tags=tags,
            )
            statsd.histogram(
                "legal_intel.llm.tokens.output",
                self._output_tokens,
                tags=tags,
            )
        if self._cost > 0:
            statsd.distribution(
                "legal_intel.llm.cost_usd",
                self._cost,
                tags=tags,
            )
        if self._error:
            statsd.increment("legal_intel.llm.errors", tags=tags)

        return False  # Do not suppress exceptions
