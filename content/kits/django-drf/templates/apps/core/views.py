"""Health probes and the JSON fallbacks for 404 and 500 outside DRF views."""

import structlog
from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import defaults

from apps.core.exceptions import error_body

API_PREFIX = "/api/"

logger = structlog.get_logger(__name__)


def healthz(_request: HttpRequest) -> JsonResponse:
    """Liveness: the process answers. Touches no dependency."""
    return JsonResponse({"status": "ok"})


def readyz(_request: HttpRequest) -> JsonResponse:
    """Readiness: the process can serve traffic, which needs the database."""
    checks = {"database": _check_database()}
    if all(result == "ok" for result in checks.values()):
        return JsonResponse({"status": "ok", "checks": checks})
    return JsonResponse({"status": "unavailable", "checks": checks}, status=503)


def _check_database() -> str:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        logger.warning("readiness_check_failed", check="database", exc_info=True)
        return "unavailable"
    return "ok"


def not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    """`handler404`: API paths get the error envelope, everything else Django's page."""
    if request.path.startswith(API_PREFIX):
        return JsonResponse(
            error_body("not_found", "The requested resource was not found."), status=404
        )
    return defaults.page_not_found(request, exception)


def server_error(request: HttpRequest) -> HttpResponse:
    """`handler500`: Django has already logged the exception with its stack trace."""
    if request.path.startswith(API_PREFIX):
        return JsonResponse(
            error_body("internal_error", "An unexpected error occurred."), status=500
        )
    return defaults.server_error(request)
