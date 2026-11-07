"""Liveness and readiness probes: outside /api/v1/, no auth, quiet in the access log."""

import asyncio

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import SessionDep

READINESS_TIMEOUT_SECONDS = 2.0

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """The process is up. Checks nothing else, so a database outage never restarts the container."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(session: SessionDep) -> JSONResponse:
    """The process can serve traffic: the database answers `SELECT 1`."""
    try:
        async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
            await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:  # TimeoutError is an OSError
        logger.warning("readiness_check_failed", check="database", error=type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "checks": {"database": "unavailable"}},
        )
    return JSONResponse(content={"status": "ok", "checks": {"database": "ok"}})
