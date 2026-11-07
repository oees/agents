from typing import Annotated

import httpx
import pytest
import structlog
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.core.request_id import REQUEST_ID_HEADER


class PaymentRequiredError(DomainError):
    code = "payment_required"
    status_code = 402


class Payload(BaseModel):
    name: str
    quantity: int


@pytest.fixture
def routes(app: FastAPI) -> FastAPI:
    @app.get("/raises/not-found")
    async def raises_not_found() -> None:
        raise NotFoundError("Widget 7 does not exist.", details={"id": 7})

    @app.get("/raises/conflict")
    async def raises_conflict() -> None:
        raise ConflictError("Widget already exists.")

    @app.get("/raises/custom")
    async def raises_custom() -> None:
        raise PaymentRequiredError("Top up first.")

    @app.get("/raises/http")
    async def raises_http() -> None:
        raise HTTPException(
            status_code=401, detail="Token expired.", headers={"WWW-Authenticate": "Bearer"}
        )

    @app.get("/raises/unexpected")
    async def raises_unexpected() -> None:
        message = "database password is hunter2"
        raise RuntimeError(message)

    @app.post("/validates")
    async def validates(payload: Payload, limit: Annotated[int, Query(le=10)] = 1) -> None:
        return None

    return app


def error_of(response: httpx.Response) -> dict[str, object]:
    body = response.json()
    assert set(body) == {"error"}
    error: dict[str, object] = body["error"]
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["request_id"] == response.headers[REQUEST_ID_HEADER]
    return error


@pytest.mark.usefixtures("routes")
async def test_domain_error_maps_to_its_status_and_code(client: httpx.AsyncClient) -> None:
    response = await client.get("/raises/not-found")

    assert response.status_code == 404
    assert error_of(response) == {
        "code": "not_found",
        "message": "Widget 7 does not exist.",
        "details": {"id": 7},
        "request_id": response.headers[REQUEST_ID_HEADER],
    }


@pytest.mark.usefixtures("routes")
@pytest.mark.parametrize(
    ("path", "status", "code"),
    [("/raises/conflict", 409, "conflict"), ("/raises/custom", 402, "payment_required")],
)
async def test_domain_error_subclasses_choose_status_and_code(
    client: httpx.AsyncClient, path: str, status: int, code: str
) -> None:
    response = await client.get(path)

    assert response.status_code == status
    assert error_of(response)["code"] == code


@pytest.mark.usefixtures("routes")
async def test_http_exception_keeps_status_message_and_headers(client: httpx.AsyncClient) -> None:
    response = await client.get("/raises/http")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    error = error_of(response)
    assert error["code"] == "not_authenticated"
    assert error["message"] == "Token expired."


async def test_unknown_route_gets_the_envelope(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/nothing-here")

    assert response.status_code == 404
    error = error_of(response)
    assert error["code"] == "not_found"
    assert error["message"] == "Not Found"


async def test_wrong_method_gets_the_envelope(client: httpx.AsyncClient) -> None:
    response = await client.post("/healthz")

    assert response.status_code == 405
    assert error_of(response)["code"] == "method_not_allowed"


@pytest.mark.usefixtures("routes")
async def test_validation_errors_are_listed_per_field(client: httpx.AsyncClient) -> None:
    response = await client.post("/validates?limit=11", json={"quantity": "many"})

    assert response.status_code == 422
    error = error_of(response)
    assert error["code"] == "validation_error"
    details = error["details"]
    assert isinstance(details, dict)
    assert set(details) == {"name", "quantity", "limit"}
    assert all(isinstance(messages, list) and messages for messages in details.values())


@pytest.mark.usefixtures("routes")
async def test_unexpected_error_hides_internals_and_logs_the_trace(
    client: httpx.AsyncClient,
) -> None:
    with structlog.testing.capture_logs() as logs:
        response = await client.get("/raises/unexpected", headers={REQUEST_ID_HEADER: "req-500"})

    assert response.status_code == 500
    error = error_of(response)
    assert error == {
        "code": "internal_error",
        "message": "An unexpected error occurred.",
        "details": None,
        "request_id": "req-500",
    }
    assert "hunter2" not in response.text
    [logged] = [entry for entry in logs if entry["event"] == "unhandled_exception"]
    assert logged["log_level"] == "error"
    assert isinstance(logged["exc_info"], RuntimeError)
