"""pytest-django and `make check`. Needs only DATABASE_URL: Celery runs tasks inline."""

from config.settings.base import *

# Long enough for HS256 token signing; never leaves the test process.
SECRET_KEY = "test-only-placeholder-not-a-secret-0123456789"  # noqa: S105
ALLOWED_HOSTS = ["testserver"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# No collectstatic before tests: no manifest, and WhiteNoise serves from the finders.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True

CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
