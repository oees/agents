"""One structured JSON logger for the CLI, tagged with a per-run id."""

import json
import logging
import sys
import uuid
from datetime import UTC, datetime

_STANDARD = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "run_id"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": getattr(record, "run_id", None),
        }
        payload.update({k: v for k, v in vars(record).items() if k not in _STANDARD})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _RunId(logging.Filter):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        return True


def configure(verbose: bool) -> str:
    """Log JSON to stderr: errors only by default, every file operation with --verbose."""
    run_id = uuid.uuid4().hex[:12]
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(_RunId(run_id))
    logger = logging.getLogger("oees_agents")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO if verbose else logging.ERROR)
    logger.propagate = False
    return run_id
