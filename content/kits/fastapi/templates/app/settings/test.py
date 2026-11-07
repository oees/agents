from typing import Literal

from pydantic import Field, SecretStr

from app.settings.base import BaseAppSettings, LogLevel


class TestSettings(BaseAppSettings):
    """Defaults plus TEST_DATABASE_URL; never .env.

    A developer's local values (log level, docs, the dev database) cannot leak into the test run.
    """

    __test__ = False  # not a pytest test class

    app_env: Literal["test"] = "test"
    log_level: LogLevel = "WARNING"
    database_url: SecretStr = Field(
        default=SecretStr("postgresql+asyncpg://postgres:postgres@localhost:5432/app_test"),
        validation_alias="TEST_DATABASE_URL",
    )
