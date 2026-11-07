"""SQLAlchemy 2 async engine, declarative base and the per-request session dependency."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import URL, MetaData, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.settings import BaseAppSettings

# Named constraints so Alembic can generate (and later drop) them deterministically.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

ASYNC_DRIVER = "postgresql+asyncpg"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def async_database_url(raw: str) -> URL:
    """Normalise a Postgres URL for asyncpg.

    Managed databases hand out `postgresql://...?sslmode=require`; asyncpg wants the
    `postgresql+asyncpg` driver and an `ssl` query parameter instead of `sslmode`.
    """
    url = make_url(raw)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername=ASYNC_DRIVER)
    if "sslmode" in url.query:
        query = dict(url.query)
        query["ssl"] = query.pop("sslmode")
        url = url.set(query=query)
    return url


def create_engine(settings: BaseAppSettings) -> AsyncEngine:
    return create_async_engine(
        async_database_url(settings.database_url.get_secret_value()),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
    )


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request.

    Services commit explicitly; closing the session rolls back anything left uncommitted.
    """
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
