"""Settings selected by `APP_ENV` (local, test, production). Always go through `get_settings()`."""

import os
from functools import lru_cache

from app.settings.base import BaseAppSettings
from app.settings.local import LocalSettings
from app.settings.production import ProductionSettings
from app.settings.test import TestSettings

SETTINGS_BY_ENV: dict[str, type[BaseAppSettings]] = {
    "local": LocalSettings,
    "test": TestSettings,
    "production": ProductionSettings,
}


class UnknownEnvironmentError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_settings() -> BaseAppSettings:
    app_env = os.environ.get("APP_ENV", "")
    try:
        settings_class = SETTINGS_BY_ENV[app_env]
    except KeyError:
        expected = ", ".join(sorted(SETTINGS_BY_ENV))
        message = f"APP_ENV must be one of {expected}; got {app_env!r}."
        raise UnknownEnvironmentError(message) from None
    return settings_class()


__all__ = ["BaseAppSettings", "UnknownEnvironmentError", "get_settings"]
