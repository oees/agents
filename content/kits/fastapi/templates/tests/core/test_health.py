from collections.abc import AsyncIterator

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import get_session


async def test_healthz_reports_ok_without_touching_dependencies(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_reports_ok_when_the_database_answers(client: httpx.AsyncClient) -> None:
    response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


async def test_readyz_reports_unavailable_when_the_database_is_unreachable(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    # Port 1 on loopback refuses connections immediately: a real failure, no mocking of SQLAlchemy.
    unreachable = create_async_engine("postgresql+asyncpg://user:pass@127.0.0.1:1/none")
    sessionmaker = async_sessionmaker(unreachable)

    async def unreachable_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = unreachable_session
    try:
        response = await client.get("/readyz")
    finally:
        app.dependency_overrides.clear()
        await unreachable.dispose()

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "checks": {"database": "unavailable"}}
