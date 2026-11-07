from typing import Literal

from pydantic_settings import SettingsConfigDict

from app.settings.base import BaseAppSettings, LogLevel


class LocalSettings(BaseAppSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_env: Literal["local"] = "local"
    log_level: LogLevel = "DEBUG"
