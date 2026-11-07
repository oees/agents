from collections.abc import Iterator

import pytest
from pydantic import SecretStr

from app.settings import UnknownEnvironmentError, get_settings
from app.settings.local import LocalSettings
from app.settings.production import ProductionSettings
from app.settings.test import TestSettings

PLACEHOLDER_URL = "postgresql+asyncpg://user:change-me@db:5432/app"


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("app_env", "settings_class"),
    [("local", LocalSettings), ("test", TestSettings), ("production", ProductionSettings)],
)
def test_app_env_selects_the_settings_class(
    monkeypatch: pytest.MonkeyPatch, app_env: str, settings_class: type
) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("DATABASE_URL", PLACEHOLDER_URL)

    assert type(get_settings()) is settings_class


@pytest.mark.parametrize("app_env", ["", "staging", "prod"])
def test_unknown_app_env_fails_loudly(monkeypatch: pytest.MonkeyPatch, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)

    with pytest.raises(UnknownEnvironmentError, match="local, production, test"):
        get_settings()


def test_settings_are_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")

    assert get_settings() is get_settings()


def test_production_hides_docs_and_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", PLACEHOLDER_URL)
    monkeypatch.delenv("DOCS_ENABLED", raising=False)

    settings = get_settings()

    assert settings.docs_enabled is False
    assert isinstance(settings.database_url, SecretStr)
    assert "change-me" not in repr(settings)


def test_production_requires_a_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="database_url"):
        get_settings()


def test_tests_read_their_own_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db/local_data")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+asyncpg://u:p@db/app_test")

    url = get_settings().database_url.get_secret_value()

    assert url.endswith("/app_test")
