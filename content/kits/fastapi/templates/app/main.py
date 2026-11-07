"""Application factory. Run with `uvicorn app.main:create_app --factory`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import API_PREFIX, api_router
from app.core.db import create_engine, create_sessionmaker
from app.core.errors import register_exception_handlers
from app.core.health import router as health_router
from app.core.http import build_http_client
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.settings import BaseAppSettings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: BaseAppSettings = app.state.settings
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.sessionmaker = create_sessionmaker(engine)
    try:
        async with build_http_client(settings) as http_client:
            app.state.http_client = http_client
            yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)
    return app
