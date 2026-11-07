"""Every versioned endpoint hangs off `api_router`. Include each domain's router here."""

from fastapi import APIRouter

API_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_PREFIX)
# api_router.include_router(<domain>.router.router)
