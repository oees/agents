import logging
import re
from typing import Any

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory
from structlog.contextvars import get_contextvars

from apps.core.middleware import RequestIdMiddleware


def _events(
    caplog: pytest.LogCaptureFixture, event: str
) -> list[tuple[int, dict[str, Any]]]:
    """structlog hands stdlib the event dict as the record's message."""
    return [
        (record.levelno, record.msg)
        for record in caplog.records
        if isinstance(record.msg, dict) and record.msg.get("event") == event
    ]


def _respond(seen: dict[str, Any]) -> RequestIdMiddleware:
    def view(_request: HttpRequest) -> HttpResponse:
        seen.update(get_contextvars())
        return HttpResponse("ok")

    return RequestIdMiddleware(view)


def test_echoes_a_valid_incoming_request_id(rf: RequestFactory) -> None:
    seen: dict[str, Any] = {}
    request = rf.get("/api/v1/things/", HTTP_X_REQUEST_ID="edge-7f3a.42_b")

    response = _respond(seen)(request)

    assert response["X-Request-ID"] == "edge-7f3a.42_b"
    assert seen["request_id"] == "edge-7f3a.42_b"


def test_generates_a_uuid4_hex_when_the_header_is_missing(rf: RequestFactory) -> None:
    seen: dict[str, Any] = {}

    response = _respond(seen)(rf.get("/api/v1/things/"))

    assert re.fullmatch(r"[0-9a-f]{32}", response["X-Request-ID"])
    assert seen["request_id"] == response["X-Request-ID"]


@pytest.mark.parametrize("incoming", ["has spaces", "line\nbreak", "x" * 129, ""])
def test_replaces_an_unsafe_incoming_request_id(
    rf: RequestFactory, incoming: str
) -> None:
    response = _respond({})(rf.get("/", HTTP_X_REQUEST_ID=incoming))

    assert re.fullmatch(r"[0-9a-f]{32}", response["X-Request-ID"])


def test_keeps_the_id_bound_for_djangos_response_logging(rf: RequestFactory) -> None:
    response = _respond({})(rf.get("/"))

    assert get_contextvars()["request_id"] == response["X-Request-ID"]


def test_clears_the_log_context_when_the_request_finishes(client: Client) -> None:
    client.get("/healthz")

    assert get_contextvars() == {}


def test_logs_each_request_once_at_info(
    rf: RequestFactory, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    response = _respond({})(rf.get("/api/v1/things/"))

    [(level, event)] = _events(caplog, "request_finished")
    assert level == logging.INFO
    assert event["request_id"] == response["X-Request-ID"]
    assert event["method"] == "GET"
    assert event["path"] == "/api/v1/things/"
    assert event["status_code"] == 200
    assert isinstance(event["duration_ms"], float)


def test_successful_health_probes_stay_out_of_info(
    rf: RequestFactory, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    _respond({})(rf.get("/healthz"))

    [(level, _event)] = _events(caplog, "request_finished")
    assert level == logging.DEBUG
