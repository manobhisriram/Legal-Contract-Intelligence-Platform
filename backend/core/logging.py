"""
backend/core/logging.py

Structured JSON logging with Datadog trace/span ID injection.
Every log line emitted by structlog will include dd.trace_id and dd.span_id
when DD_LOGS_INJECTION=true — this lets Datadog correlate logs with APM traces.
"""
import structlog
import logging
import sys
from backend.core.config import settings


def _add_datadog_trace_context(logger, method, event_dict):
    """
    structlog processor that injects Datadog trace/span IDs into every log record.
    When DD_LOGS_INJECTION is enabled, ddtrace injects these automatically into
    the Python logging module. We extract them here for structlog compatibility.
    """
    try:
        from ddtrace import tracer
        span = tracer.current_span()
        if span:
            trace_id = span.trace_id
            span_id = span.span_id
            # Datadog expects trace IDs in decimal string format
            event_dict["dd.trace_id"] = str(trace_id) if trace_id else "0"
            event_dict["dd.span_id"] = str(span_id) if span_id else "0"
            event_dict["dd.service"] = settings.dd_service
            event_dict["dd.env"] = settings.effective_dd_env
            event_dict["dd.version"] = settings.app_version
    except ImportError:
        pass
    except Exception:
        pass
    return event_dict


def setup_logging():
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        _add_datadog_trace_context,           # inject DD trace IDs
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),  # JSON output → Datadog Logs auto-parses
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)
