from typing import Literal

from app.settings.base import BaseAppSettings


class ProductionSettings(BaseAppSettings):
    """Only real environment variables; no .env file is read in production."""

    app_env: Literal["production"] = "production"
    docs_enabled: bool = False
