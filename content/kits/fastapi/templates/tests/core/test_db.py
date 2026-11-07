import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, UniqueConstraint
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy.schema import CreateTable

from app.core.db import NAMING_CONVENTION, async_database_url, create_engine
from app.settings import get_settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@db:5432/app", "postgresql+asyncpg://u:p@db:5432/app"),
        ("postgresql://u:p@db:5432/app", "postgresql+asyncpg://u:p@db:5432/app"),
        (
            "postgresql://u:p@db:25060/app?sslmode=require",
            "postgresql+asyncpg://u:p@db:25060/app?ssl=require",
        ),
        ("postgresql+asyncpg://u:p@db/app", "postgresql+asyncpg://u:p@db/app"),
    ],
)
def test_database_urls_are_normalised_for_asyncpg(raw: str, expected: str) -> None:
    assert async_database_url(raw).render_as_string(hide_password=False) == expected


def test_constraints_get_deterministic_names() -> None:
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    Table("customer", metadata, Column("id", Integer, primary_key=True))
    orders = Table(
        "orders",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("customer_id", ForeignKey("customer.id")),
        Column("reference", String(20)),
        UniqueConstraint("reference"),
    )

    ddl = str(CreateTable(orders))

    assert "CONSTRAINT pk_orders" in ddl
    assert "CONSTRAINT uq_orders_reference" in ddl
    assert "CONSTRAINT fk_orders_customer_id_customer" in ddl


async def test_engine_uses_the_pool_settings() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        assert engine.dialect.driver == "asyncpg"
        assert isinstance(engine.pool, AsyncAdaptedQueuePool)
        assert engine.pool.size() == settings.database_pool_size
    finally:
        await engine.dispose()
