"""Structured JSON logging to stdout, shared by the web process and the Celery worker.

structlog loggers and stdlib loggers (Django, Celery, gunicorn) go through the same
processor chain, so every line is one JSON object carrying the bound context
(`request_id`, `task_id`, `task_name`) with secrets and personal data redacted.
"""

from collections.abc import Mapping
from typing import Any

import structlog
import structlog.tracebacks
from structlog.typing import EventDict, Processor, WrappedLogger

REDACTED = "[REDACTED]"

# Keys whose values never reach the logs, matched case-insensitively.
SENSITIVE_KEYS = frozenset(
    {
        "address",
        "dni",
        "email",
        "iban",
        "nie",
        "nif",
        "phone",
    }
)

# Any key containing one of these fragments is redacted too (`refresh_token`,
# `db_password`, ...).
SENSITIVE_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "secret",
    "session",
    "token",
)


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return lowered in SENSITIVE_KEYS or any(
        fragment in lowered for fragment in SENSITIVE_FRAGMENTS
    )


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: REDACTED if _is_sensitive(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value]
    return value


def redact_sensitive(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """Replace the value of every sensitive key, at any nesting depth, with a marker."""
    return {
        key: REDACTED if _is_sensitive(key) else _redact(value)
        for key, value in event_dict.items()
    }


SHARED_PROCESSORS: tuple[Processor, ...] = (
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    redact_sensitive,
)


def json_formatter() -> structlog.stdlib.ProcessorFormatter:
    """Render any log record, structlog or stdlib, as one JSON line."""
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            # Structured tracebacks without frame locals, which hold passwords and PII.
            structlog.processors.ExceptionRenderer(
                structlog.tracebacks.ExceptionDictTransformer(show_locals=False)
            ),
            structlog.processors.JSONRenderer(),
        ],
    )


def build_logging_config(level: str) -> dict[str, Any]:
    """The `LOGGING` dict for Django settings: one stdout handler, JSON lines."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": "apps.core.logging.json_formatter"}},
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "json",
            },
        },
        "root": {"handlers": ["stdout"], "level": level},
        "loggers": {
            # RequestIdMiddleware logs every request once; runserver's lines repeat it.
            "django.server": {"level": "WARNING"},
        },
    }


def clear_log_context(**_kwargs: Any) -> None:
    """Connected to `request_finished`, after Django's response logging used the id."""
    structlog.contextvars.clear_contextvars()


def configure_structlog() -> None:
    """Route structlog through stdlib logging so the `LOGGING` handlers render it."""
    structlog.configure(
        processors=[
            *SHARED_PROCESSORS,
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
