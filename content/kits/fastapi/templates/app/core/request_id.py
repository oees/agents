"""Request id and access log, as a pure ASGI middleware.

Pure ASGI (not `BaseHTTPMiddleware`) so the context variables it binds are visible to the endpoint,
its dependencies and the exception handlers, and so streaming responses are not buffered.
"""

import re
import time
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
# Incoming ids are echoed into logs and headers, so only accept a conservative shape.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
# Probes hit these every few seconds; successful calls are logged at DEBUG to keep noise down.
QUIET_PATHS: frozenset[str] = frozenset({"/healthz", "/readyz"})

logger = structlog.get_logger(__name__)


def current_request_id() -> str | None:
    """The id of the request being handled, or None outside a request."""
    value = structlog.contextvars.get_contextvars().get("request_id")
    return value if isinstance(value, str) else None


def _incoming_or_new(scope: Scope) -> str:
    incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
    if incoming is not None and _VALID_REQUEST_ID.fullmatch(incoming):
        return incoming
    return uuid.uuid4().hex


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_or_new(scope)
        scope.setdefault("state", {})["request_id"] = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        status_code = 500  # stays 500 when the app raises before sending a response
        started = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            path: str = scope["path"]
            fields = {
                "method": scope["method"],
                "path": path,
                "status": status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            if path in QUIET_PATHS and status_code < 400:
                logger.debug("request", **fields)
            else:
                logger.info("request", **fields)
