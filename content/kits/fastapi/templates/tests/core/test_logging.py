import io
import json
import logging
import logging.config
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog

from app.core.logging import REDACTED, configure_logging, redact_sensitive

UVICORN_LOG_CONFIG = Path(__file__).resolve().parents[2] / "app" / "core" / "uvicorn_logging.json"


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    configure_logging("INFO", stream=buffer)
    yield buffer
    structlog.contextvars.clear_contextvars()


def lines(buffer: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in buffer.getvalue().splitlines()]


def test_structlog_lines_are_json_with_the_bound_request_id(stream: io.StringIO) -> None:
    structlog.contextvars.bind_contextvars(request_id="req-7")

    structlog.get_logger("app.test").info("order_created", order_id=3)

    [line] = lines(stream)
    assert line["event"] == "order_created"
    assert line["order_id"] == 3
    assert line["request_id"] == "req-7"
    assert line["level"] == "info"
    assert line["logger"] == "app.test"
    assert "timestamp" in line


def test_standard_library_loggers_share_the_format(stream: io.StringIO) -> None:
    structlog.contextvars.bind_contextvars(request_id="req-8")

    logging.getLogger("uvicorn.error").warning("worker %s restarted", 2)

    [line] = lines(stream)
    assert line["event"] == "worker 2 restarted"
    assert line["request_id"] == "req-8"
    assert line["level"] == "warning"


def test_exceptions_are_rendered_with_the_traceback(stream: io.StringIO) -> None:
    try:
        message = "boom"
        raise ValueError(message)
    except ValueError:
        structlog.get_logger("app.test").exception("failed")

    [line] = lines(stream)
    assert "ValueError: boom" in str(line["exception"])


def test_lines_below_the_level_are_dropped(stream: io.StringIO) -> None:
    structlog.get_logger("app.test").debug("noise")

    assert lines(stream) == []


def test_sensitive_keys_are_redacted_at_any_depth() -> None:
    event = {
        "event": "login",
        "password": "pw",
        "Authorization": "Bearer x",
        "dni": "00000000T",
        "unified_view": "kept",
        "payload": {"refresh_token": "t", "nested": [{"client_secret": "s", "name": "kept"}]},
    }

    redacted = redact_sensitive(None, "info", event)

    assert redacted == {
        "event": "login",
        "password": REDACTED,
        "Authorization": REDACTED,
        "dni": REDACTED,
        "unified_view": "kept",
        "payload": {
            "refresh_token": REDACTED,
            "nested": [{"client_secret": REDACTED, "name": "kept"}],
        },
    }


def test_uvicorn_supervisor_config_renders_json(capsys: pytest.CaptureFixture[str]) -> None:
    logging.config.dictConfig(json.loads(UVICORN_LOG_CONFIG.read_text()))

    logging.getLogger("uvicorn.error").info("Started parent process [%d]", 1)

    [line] = [json.loads(raw) for raw in capsys.readouterr().out.splitlines()]
    assert line["event"] == "Started parent process [1]"
    assert line["logger"] == "uvicorn.error"
    assert line["level"] == "info"
