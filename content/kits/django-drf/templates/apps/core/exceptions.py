"""The error envelope for every non-2xx API response.

    {"error": {"code": "snake_case_code", "message": "Human readable sentence.",
               "details": {...} | null, "request_id": "..."}}

Wired as `REST_FRAMEWORK["EXCEPTION_HANDLER"]`. Validation details are
`{"field": ["message", ...]}`; unexpected exceptions are logged at ERROR with the stack
trace and answered with `internal_error`, never with the exception text.
"""

from collections.abc import Mapping
from typing import Any

import structlog
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import set_rollback
from structlog.contextvars import get_contextvars

logger = structlog.get_logger(__name__)

VALIDATION_MESSAGE = "The request is invalid."
INTERNAL_MESSAGE = "An unexpected error occurred."


def error_body(
    code: str, message: str, details: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": get_contextvars().get("request_id"),
        }
    }


def exception_handler(exc: Exception, context: Mapping[str, Any]) -> Response:
    exc = _as_api_exception(exc)
    set_rollback()
    if not isinstance(exc, exceptions.APIException):
        view = context.get("view")
        logger.error("unhandled_exception", view=type(view).__name__, exc_info=exc)
        return Response(
            error_body("internal_error", INTERNAL_MESSAGE),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        body = error_body(
            "validation_error", VALIDATION_MESSAGE, _field_errors(exc.detail)
        )
    else:
        code, message = _code_and_message(exc)
        body = error_body(code, message)
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error("api_exception", code=body["error"]["code"], exc_info=exc)
    return Response(body, status=exc.status_code, headers=_headers(exc))


def _as_api_exception(exc: Exception) -> Exception:
    """Translate the Django exceptions DRF also understands."""
    if isinstance(exc, Http404):
        return exceptions.NotFound()
    if isinstance(exc, DjangoPermissionDenied):
        return exceptions.PermissionDenied()
    if isinstance(exc, DjangoValidationError):
        return exceptions.ValidationError(as_serializer_error(exc))
    return exc


def _field_errors(detail: Any) -> dict[str, Any]:
    if isinstance(detail, Mapping):
        return {str(field): _messages(errors) for field, errors in detail.items()}
    return {"non_field_errors": _messages(detail)}


def _messages(errors: Any) -> Any:
    if isinstance(errors, Mapping):
        return _field_errors(errors)
    if isinstance(errors, list):
        return [_messages(item) for item in errors]
    return str(errors)


def _code_and_message(exc: exceptions.APIException) -> tuple[str, str]:
    detail: object = exc.detail
    # simplejwt and some third-party errors carry {"detail": ..., "code": ...} dicts.
    if isinstance(detail, Mapping):
        detail = detail.get("detail", exc.default_detail)
    code = getattr(detail, "code", None) or exc.default_code
    return str(code), str(detail)


def _headers(exc: exceptions.APIException) -> dict[str, str]:
    headers: dict[str, str] = {}
    auth_header = getattr(exc, "auth_header", None)
    if auth_header:
        headers["WWW-Authenticate"] = str(auth_header)
    wait = getattr(exc, "wait", None)
    if wait is not None:
        headers["Retry-After"] = str(int(wait))
    return headers
