from collections.abc import Iterator

import httpx
import pytest
from fastapi import FastAPI

from app.main import create_app
from app.settings import get_settings


@pytest.fixture
def production_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:change-me@db:5432/app")
    monkeypatch.delenv("DOCS_ENABLED", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_lifespan_opens_and_closes_shared_resources() -> None:
    app = create_app()

    async with app.router.lifespan_context(app):
        http_client: httpx.AsyncClient = app.state.http_client
        assert not http_client.is_closed

    assert http_client.is_closed


async def test_api_docs_are_served_under_the_versioned_prefix(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert "/healthz" in response.json()["paths"]


@pytest.mark.usefixtures("production_env")
def test_production_does_not_serve_api_docs() -> None:
    app: FastAPI = create_app()

    assert app.openapi_url is None
    assert app.docs_url is None
