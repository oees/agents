import io
import json
import logging
from collections.abc import Iterator

import pytest
import structlog
from structlog.contextvars import bind_contextvars

from apps.core.logging import (
    REDACTED,
    build_logging_config,
    json_formatter,
    redact_sensitive,
)


@pytest.fixture
def output() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(json_formatter())
    logger = logging.getLogger("tests.json")
    logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    yield stream
    logger.removeHandler(handler)


def _lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_structlog_events_render_as_json_with_the_bound_context(
    output: io.StringIO,
) -> None:
    bind_contextvars(request_id="req-9")

    structlog.get_logger("tests.json").info("invoice_sent", invoice_id=7)

    [line] = _lines(output)
    assert line["event"] == "invoice_sent"
    assert line["invoice_id"] == 7
    assert line["request_id"] == "req-9"
    assert line["level"] == "info"
    assert line["logger"] == "tests.json"
    assert "timestamp" in line


def test_stdlib_records_render_as_json_with_a_structured_traceback(
    output: io.StringIO,
) -> None:
    bind_contextvars(request_id="req-10")

    try:
        raise ValueError("bad input")
    except ValueError:
        logging.getLogger("tests.json").exception("import_failed")

    [line] = _lines(output)
    assert line["event"] == "import_failed"
    assert line["request_id"] == "req-10"
    assert line["level"] == "error"
    assert isinstance(line["exception"], list)


def test_tracebacks_leave_out_frame_locals(output: io.StringIO) -> None:
    def connect(password: str) -> None:
        raise ConnectionError("refused")

    try:
        connect(password="hunter2")
    except ConnectionError:
        structlog.get_logger("tests.json").exception("connect_failed")

    assert "refused" in output.getvalue()
    assert "hunter2" not in output.getvalue()


def test_sensitive_values_never_reach_the_output(output: io.StringIO) -> None:
    structlog.get_logger("tests.json").info(
        "login",
        password="hunter2",
        Authorization="Bearer abc",
        payload={"refresh_token": "xyz"},
    )

    rendered = output.getvalue()
    assert "hunter2" not in rendered
    assert "Bearer abc" not in rendered
    assert "xyz" not in rendered


def test_redaction_covers_nested_keys_and_personal_data() -> None:
    event = redact_sensitive(
        None,
        "info",
        {
            "event": "customer_updated",
            "customer": {
                "id": 3,
                "Email": "ana@example.com",
                "contacts": [{"phone": "600"}],
            },
            "db_password": "x",
        },
    )

    assert event == {
        "event": "customer_updated",
        "customer": {"id": 3, "Email": REDACTED, "contacts": [{"phone": REDACTED}]},
        "db_password": REDACTED,
    }


def test_logging_config_writes_json_to_stdout_only() -> None:
    config = build_logging_config("WARNING")

    assert config["root"] == {"handlers": ["stdout"], "level": "WARNING"}
    assert config["handlers"]["stdout"]["stream"] == "ext://sys.stdout"
    assert config["handlers"]["stdout"]["formatter"] == "json"
