from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest
import structlog

from app.core.http import RetryTransport, build_http_client
from app.core.request_id import REQUEST_ID_HEADER
from app.settings import get_settings


class Upstream:
    """An httpx.MockTransport handler that answers with the queued statuses in order."""

    def __init__(self, *statuses: int, headers: dict[str, str] | None = None) -> None:
        self.statuses = list(statuses)
        self.headers = headers or {}
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.statuses.pop(0), headers=self.headers)


class RecordingSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def client_for(upstream: Upstream, sleep: RecordingSleep) -> httpx.AsyncClient:
    return build_http_client(get_settings(), transport=httpx.MockTransport(upstream), sleep=sleep)


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
async def test_retries_idempotent_requests_on_retryable_statuses(status: int) -> None:
    upstream, sleep = Upstream(status, 200), RecordingSleep()

    async with client_for(upstream, sleep) as client:
        response = await client.get("https://upstream.test/items")

    assert response.status_code == 200
    assert len(upstream.requests) == 2
    assert len(sleep.delays) == 1


async def test_backs_off_exponentially_with_jitter_until_attempts_run_out() -> None:
    upstream, sleep = Upstream(503, 503, 503), RecordingSleep()

    async with client_for(upstream, sleep) as client:
        response = await client.put("https://upstream.test/items/1", json={"name": "x"})

    assert response.status_code == 503
    assert len(upstream.requests) == get_settings().http_max_attempts == 3
    first, second = sleep.delays
    assert 0.125 <= first <= 0.25
    assert 0.25 <= second <= 0.5


@pytest.mark.parametrize("method", ["POST", "PATCH"])
async def test_never_retries_non_idempotent_methods(method: str) -> None:
    upstream, sleep = Upstream(503), RecordingSleep()

    async with client_for(upstream, sleep) as client:
        response = await client.request(method, "https://upstream.test/items")

    assert response.status_code == 503
    assert len(upstream.requests) == 1
    assert sleep.delays == []


@pytest.mark.parametrize("status", [400, 404, 409])
async def test_does_not_retry_client_errors(status: int) -> None:
    upstream, sleep = Upstream(status), RecordingSleep()

    async with client_for(upstream, sleep) as client:
        response = await client.get("https://upstream.test/items")

    assert response.status_code == status
    assert len(upstream.requests) == 1


@pytest.mark.parametrize(("retry_after", "expected"), [("2", 2.0), ("60", 5.0)])
async def test_honours_retry_after_seconds_capped_at_the_backoff_max(
    retry_after: str, expected: float
) -> None:
    upstream = Upstream(429, 429, 200, headers={"Retry-After": retry_after})
    sleep = RecordingSleep()

    async with client_for(upstream, sleep) as client:
        await client.get("https://upstream.test/items")

    assert sleep.delays == [expected, expected]


async def test_honours_retry_after_http_dates() -> None:
    soon = format_datetime(datetime.now(UTC) + timedelta(seconds=3), usegmt=True)
    upstream, sleep = Upstream(503, 200, headers={"Retry-After": soon}), RecordingSleep()

    async with client_for(upstream, sleep) as client:
        await client.get("https://upstream.test/items")

    [delay] = sleep.delays
    assert 0 < delay <= 3


async def test_logs_each_retry_without_the_query_string() -> None:
    upstream, sleep = Upstream(503, 200), RecordingSleep()

    with structlog.testing.capture_logs() as logs:
        async with client_for(upstream, sleep) as client:
            await client.get("https://upstream.test/items?token=abc")

    [retry] = [entry for entry in logs if entry["event"] == "http_retry"]
    assert retry["host"] == "upstream.test"
    assert retry["path"] == "/items"
    assert "abc" not in str(retry)


async def test_propagates_the_current_request_id() -> None:
    upstream, sleep = Upstream(200), RecordingSleep()

    with structlog.contextvars.bound_contextvars(request_id="req-42"):
        async with client_for(upstream, sleep) as client:
            await client.get("https://upstream.test/items")

    assert upstream.requests[0].headers[REQUEST_ID_HEADER] == "req-42"


async def test_sends_no_request_id_outside_a_request() -> None:
    upstream, sleep = Upstream(200), RecordingSleep()
    structlog.contextvars.clear_contextvars()

    async with client_for(upstream, sleep) as client:
        await client.get("https://upstream.test/items")

    assert REQUEST_ID_HEADER not in upstream.requests[0].headers


async def test_sets_explicit_timeouts() -> None:
    settings = get_settings()

    async with build_http_client(settings) as client:
        assert client.timeout == httpx.Timeout(
            settings.http_timeout_seconds, connect=settings.http_connect_timeout_seconds
        )


def test_rejects_fewer_than_one_attempt() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        RetryTransport(httpx.MockTransport(Upstream()), max_attempts=0)
