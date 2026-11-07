"""One URL per screen: the full page, or only the named partial for htmx requests."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

import structlog
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.cache import patch_vary_headers
from django_htmx.http import HttpResponseClientRedirect
from django_htmx.middleware import HtmxDetails

logger = structlog.get_logger(__name__)

MESSAGES_PARTIAL = "core/partials/messages.html"


class HtmxHttpRequest(HttpRequest):
    """An HttpRequest after django-htmx's HtmxMiddleware has run."""

    htmx: HtmxDetails


def wants_partial(request: HtmxHttpRequest) -> bool:
    """Boosted links and history restores replace the whole body: full page."""
    return (
        bool(request.htmx)
        and not request.htmx.boosted
        and not request.htmx.history_restore_request
    )


def htmx_screen(
    request: HtmxHttpRequest,
    template_name: str,
    partial_name: str,
    context: Mapping[str, Any] | None = None,
    *,
    status: int = HTTPStatus.OK,
) -> HttpResponse:
    """Render a screen.

    ``template_name`` is the full page and includes ``partial_name``. An htmx
    request gets the partial plus an out-of-band update of ``#messages``, so
    outcomes queued with the messages framework show up without a page load.
    """
    partial = wants_partial(request)
    if partial:
        body = render_to_string(partial_name, context, request) + render_to_string(
            MESSAGES_PARTIAL, {"oob": True}, request
        )
    else:
        body = render_to_string(template_name, context, request)
    logger.debug(
        "screen_rendered",
        template=partial_name if partial else template_name,
        partial=partial,
        status=int(status),
    )
    response = HttpResponse(body, status=status)
    # The same URL answers with a page or a fragment; caches must keep them apart.
    patch_vary_headers(response, ("HX-Request",))
    return response


def htmx_redirect(request: HtmxHttpRequest, url: str) -> HttpResponse:
    """Redirect after a successful POST: HX-Redirect for htmx, a plain 302 otherwise."""
    if request.htmx:
        return HttpResponseClientRedirect(url)
    return HttpResponseRedirect(url)
