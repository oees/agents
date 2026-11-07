"""Request correlation and health probes.

`RequestIdMiddleware` goes first in `MIDDLEWARE` so every later log line carries the id.
`HealthCheckMiddleware` goes second, before `SecurityMiddleware` and host validation:
probes from Docker and App Platform reach the container over plain HTTP with a Host
header that is not in `ALLOWED_HOSTS`, and must still be answered.
"""

import re
import time
import uuid
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse
from structlog.contextvars import bind_contextvars, clear_contextvars

from apps.core.views import healthz, readyz

REQUEST_ID_HEADER = "X-Request-ID"
# Accept a caller's id only when it is short and log-safe; otherwise mint our own.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
HEALTH_PATHS: dict[str, Callable[[HttpRequest], HttpResponse]] = {
    "/healthz": healthz,
    "/readyz": readyz,
}

logger = structlog.get_logger(__name__)


def resolve_request_id(incoming: str | None) -> str:
    if incoming and _VALID_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid.uuid4().hex


class RequestIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        clear_contextvars()
        bind_contextvars(request_id=request_id)
        started = time.perf_counter()
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = request_id
        log = logger.debug if _is_quiet(request, response) else logger.info
        log(
            "request_finished",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        return response


def _is_quiet(request: HttpRequest, response: HttpResponse) -> bool:
    """Successful health probes run every few seconds; keep them out of INFO."""
    return request.path in HEALTH_PATHS and response.status_code < 400


class HealthCheckMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        view = HEALTH_PATHS.get(request.path)
        if view is not None and request.method in ("GET", "HEAD"):
            return view(request)
        return self.get_response(request)
