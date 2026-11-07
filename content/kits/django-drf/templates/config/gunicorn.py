"""Gunicorn settings for the container (`--config python:config.gunicorn`)."""

import os

from apps.core.logging import build_logging_config

bind = "0.0.0.0:8000"
workers = 3
# App Platform's load balancer sets X-Forwarded-*; nothing else reaches the container.
forwarded_allow_ips = "*"
control_socket_disable = True

# Gunicorn's own lines go out as the same JSON as the app's. Its access log stays off:
# RequestIdMiddleware already logs each request once, with its request_id.
_level = os.environ.get("LOG_LEVEL", "INFO")
_logging = build_logging_config(_level)
# Gunicorn attaches plain-text handlers and turns propagation off; replace both.
_logging["loggers"]["gunicorn.error"] = {
    "handlers": ["stdout"],
    "level": _level,
    "propagate": False,
}
_logging["loggers"]["gunicorn.access"] = {
    "handlers": [],
    "level": "WARNING",
    "propagate": False,
}
logconfig_dict = _logging
