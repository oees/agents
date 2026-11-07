"""Structured JSON logging to stdout with structlog.

Every line is one JSON object. `request_id`, and anything else bound with
`structlog.contextvars.bind_contextvars`, is merged into each line. Standard-library loggers
(uvicorn, SQLAlchemy, Alembic) go through the same renderer, so the process speaks one format.
"""

import logging
import sys
from collections.abc import Mapping
from typing import Any, TextIO

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

REDACTED = "[REDACTED]"

# A key is redacted when its lowercased name contains any of these fragments.
SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "database_url",
    "dsn",
    "email",
    "phone",
    "iban",
)
# Short identifiers are matched exactly so they do not catch unrelated keys.
SENSITIVE_KEYS: frozenset[str] = frozenset({"dni", "nie", "nif"})


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return lowered in SENSITIVE_KEYS or any(
        fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS
    )


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: REDACTED if isinstance(key, str) and _is_sensitive(key) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value]
    return value


def redact_sensitive(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    """Replace the value of every sensitive key, at any depth, with `[REDACTED]`."""
    for key in list(event_dict):
        if _is_sensitive(key):
            event_dict[key] = REDACTED
        else:
            event_dict[key] = _redact(event_dict[key])
    return event_dict


def _shared_processors() -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        redact_sensitive,
    ]


def json_formatter() -> logging.Formatter:
    """The JSON formatter for standard-library records.

    Also referenced by `uvicorn_logging.json`, so uvicorn's supervisor process (which never imports
    the app) logs in the same format when it runs several workers.
    """
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_shared_processors(),
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
    )


def configure_logging(level: str, stream: TextIO | None = None) -> None:
    """Configure structlog and the standard library to write JSON lines to `stream` (stdout)."""
    shared = _shared_processors()
    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(json_formatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # uvicorn installs its own handlers; route its records through ours instead. Its access log is
    # replaced by the request middleware's access line.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        # Not cached, so reconfiguring (tests, Alembic) takes effect on module-level loggers too.
        cache_logger_on_first_use=False,
    )
