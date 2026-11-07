import httpx
import pytest
import structlog
from fastapi import FastAPI

from app.core.request_id import REQUEST_ID_HEADER, current_request_id


async def test_generates_a_request_id_when_none_is_sent(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")

    request_id = response.headers[REQUEST_ID_HEADER]
    assert len(request_id) == 32
    int(request_id, 16)  # uuid4 hex


async def test_echoes_a_valid_incoming_request_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz", headers={REQUEST_ID_HEADER: "abc-123.DEF_4"})

    assert response.headers[REQUEST_ID_HEADER] == "abc-123.DEF_4"


@pytest.mark.parametrize("incoming", ["has spaces", "x" * 129, "line\\nbreak", 'quote"'])
async def test_replaces_an_unsafe_incoming_request_id(
    client: httpx.AsyncClient, incoming: str
) -> None:
    response = await client.get("/healthz", headers={REQUEST_ID_HEADER: incoming})

    assert response.headers[REQUEST_ID_HEADER] != incoming
    assert len(response.headers[REQUEST_ID_HEADER]) == 32


async def test_request_id_is_bound_for_the_endpoint(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    seen: list[str | None] = []

    @app.get("/probe")
    async def probe() -> dict[str, str]:
        seen.append(current_request_id())
        return {}

    await client.get("/probe", headers={REQUEST_ID_HEADER: "req-1"})

    assert seen == ["req-1"]


async def test_logs_one_access_line_per_request(client: httpx.AsyncClient) -> None:
    with structlog.testing.capture_logs() as logs:
        await client.get("/api/v1/does-not-exist")

    access = [entry for entry in logs if entry["event"] == "request"]
    assert len(access) == 1
    assert access[0]["log_level"] == "info"
    assert access[0]["method"] == "GET"
    assert access[0]["path"] == "/api/v1/does-not-exist"
    assert access[0]["status"] == 404
    assert isinstance(access[0]["duration_ms"], float)


async def test_successful_probes_are_logged_at_debug(client: httpx.AsyncClient) -> None:
    with structlog.testing.capture_logs() as logs:
        await client.get("/healthz")

    access = [entry for entry in logs if entry["event"] == "request"]
    assert [entry["log_level"] for entry in access] == ["debug"]
