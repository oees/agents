"""Domain exceptions and the error envelope every non-2xx JSON response uses.

    {"error": {"code": "snake_case_code", "message": "...", "details": {...} | null,
               "request_id": "..."}}

Services raise a `DomainError` subclass; they never build HTTP responses. Routers do not catch
domain errors either: the handlers registered here map them to status codes.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, ClassVar

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_id import REQUEST_ID_HEADER

logger = structlog.get_logger(__name__)


class DomainError(Exception):
    """Base class for errors a service raises on purpose. Subclass per meaning, not call site."""

    code: ClassVar[str] = "domain_error"
    status_code: ClassVar[int] = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    code = "not_found"
    status_code = HTTPStatus.NOT_FOUND


class ConflictError(DomainError):
    code = "conflict"
    status_code = HTTPStatus.CONFLICT


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = HTTPStatus.FORBIDDEN


class ExternalServiceError(DomainError):
    """An upstream dependency failed or answered with something we cannot use."""

    code = "external_service_error"
    status_code = HTTPStatus.BAD_GATEWAY


HTTP_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    406: "not_acceptable",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "unprocessable_entity",
    429: "too_many_requests",
    503: "service_unavailable",
}


def _request_id(request: Request) -> str | None:
    value = request.scope.get("state", {}).get("request_id")
    return value if isinstance(value, str) else None


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    response_headers = dict(headers or {})
    if request_id is not None:
        # Set here too: the unhandled-exception response is sent outside the request-id middleware.
        response_headers[REQUEST_ID_HEADER] = request_id
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=body, headers=response_headers)


def _status_message(status_code: int) -> str:
    try:
        return f"{HTTPStatus(status_code).phrase}."
    except ValueError:
        return "Request failed."


def validation_details(exc: RequestValidationError) -> dict[str, list[str]]:
    """`{"field": ["message", ...]}`, with the location prefix (body, query, path...) dropped."""
    details: dict[str, list[str]] = {}
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ())]
        field = ".".join(location[1:]) or (location[0] if location else "non_field_errors")
        details.setdefault(field, []).append(str(error.get("msg", "Invalid value.")))
    return details


async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    logger.info("domain_error", code=exc.code, status=exc.status_code)
    return error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else _status_message(exc.status_code)
    return error_response(
        request,
        status_code=exc.status_code,
        code=HTTP_STATUS_CODES.get(exc.status_code, "http_error"),
        message=message,
        headers=exc.headers,
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        request,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="The request is not valid.",
        details=validation_details(exc),
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        exc_info=exc,
    )
    return error_response(
        request,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    # Starlette's HTTPException (not FastAPI's) so router-level 404/405 get the envelope too.
    # `Exception` is served by Starlette's outermost ServerErrorMiddleware, which re-raises after
    # responding so the server also records the failure.
    app.exception_handler(DomainError)(handle_domain_error)
    app.exception_handler(StarletteHTTPException)(handle_http_exception)
    app.exception_handler(RequestValidationError)(handle_validation_error)
    app.exception_handler(Exception)(handle_unexpected_error)
