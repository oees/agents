"""Local development in compose. Never used outside a developer machine."""

from config.settings.base import *

DEBUG = True
SECRET_KEY = env.str("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: S104 - local compose only.

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "rest_framework_simplejwt.authentication.JWTAuthentication",
    # Lets the browsable API reuse an admin login while developing.
    "rest_framework.authentication.SessionAuthentication",
]

CELERY_BROKER_URL = env.str("REDIS_URL")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
