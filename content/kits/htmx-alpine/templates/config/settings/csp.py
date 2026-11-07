"""Strict Content Security Policy for server-rendered screens (django-csp 4.x).

Imported by config/settings/base.py:

    from config.settings.csp import CONTENT_SECURITY_POLICY

and enforced by "csp.middleware.CSPMiddleware" in MIDDLEWARE. Everything the
browser runs or styles with comes from our own static files: no inline code,
no eval, no CDN.
"""

from typing import Any

from csp.constants import NONE, SELF

CONTENT_SECURITY_POLICY: dict[str, Any] = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF],
        "style-src": [SELF],
        "img-src": [SELF],
        "font-src": [SELF],
        "connect-src": [SELF],
        "form-action": [SELF],
        "object-src": [NONE],
        "base-uri": [NONE],
        "frame-ancestors": [NONE],
    },
}
