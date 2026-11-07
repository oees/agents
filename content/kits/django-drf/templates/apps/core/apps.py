from django.apps import AppConfig
from django.core.signals import request_finished

# apps.py loads before the app registry is ready: import nothing that pulls in models.
from apps.core.logging import clear_log_context, configure_structlog


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self) -> None:
        # Django has applied settings.LOGGING by now; structlog renders through it.
        configure_structlog()
        request_finished.connect(
            clear_log_context, dispatch_uid="core.clear_log_context"
        )
