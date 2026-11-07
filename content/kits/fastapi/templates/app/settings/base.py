"""Settings shared by every environment. Each environment module subclasses `BaseAppSettings`."""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class BaseAppSettings(BaseSettings):
    """Read from environment variables, case-insensitively. Secrets are `SecretStr`."""

    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    app_env: str
    app_name: str = "app"
    log_level: LogLevel = "INFO"
    docs_enabled: bool = True

    database_url: SecretStr
    database_pool_size: int = 5
    database_max_overflow: int = 5

    http_timeout_seconds: float = 10.0
    http_connect_timeout_seconds: float = 3.0
    http_connect_retries: int = 2
    http_max_attempts: int = 3
