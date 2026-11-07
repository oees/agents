import os

from celery import Celery

# Connects the logging and task-context signal handlers.
import apps.core.celery_signals  # noqa: F401

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
