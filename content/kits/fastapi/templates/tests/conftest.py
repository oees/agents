"""Shared fixtures. Tests always run with `APP_ENV=test` against the test database.

The schema comes from the real migrations, applied once per session. Every test runs inside a
transaction that is rolled back afterwards, so services can `commit()` and tests stay isolated.
"""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.db import async_database_url, get_session
from app.main import create_app
from app.settings import get_settings

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def pytest_configure(config: pytest.Config) -> None:
    os.environ["APP_ENV"] = "test"
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def migrated_database() -> None:
    command.upgrade(Config(str(ALEMBIC_INI)), "head")


@pytest.fixture
async def db_session(migrated_database: None) -> AsyncIterator[AsyncSession]:
    url = async_database_url(get_settings().database_url.get_secret_value())
    engine = create_async_engine(url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def app(db_session: AsyncSession) -> AsyncIterator[FastAPI]:
    application = create_app()

    async def override_session() -> AsyncSession:
        return db_session

    application.dependency_overrides[get_session] = override_session
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    # raise_app_exceptions=False: assert on the 500 envelope instead of the re-raised exception.
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
