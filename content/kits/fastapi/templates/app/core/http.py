"""The shared outbound HTTP client.

One `httpx.AsyncClient` per process, created in the app lifespan, so connections are pooled. It has:

- explicit timeouts (no httpx default left implicit);
- connect-error retries in `httpx.AsyncHTTPTransport(retries=...)`;
- `RetryTransport` on top: idempotent methods are retried with exponential backoff and jitter on
  429 and 5xx, honouring `Retry-After`;
- the current request id sent upstream as `X-Request-ID`.

Tests pass an `httpx.MockTransport` as `transport`; nothing in the test suite touches the network.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Annotated

import httpx
import structlog
from fastapi import Depends, Request

from app.core.request_id import REQUEST_ID_HEADER, current_request_id
from app.settings import BaseAppSettings

IDEMPOTENT_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

Sleep = Callable[[float], Awaitable[None]]

logger = structlog.get_logger(__name__)


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """`Retry-After` (delta-seconds or HTTP-date) as seconds from now; None if absent or invalid."""
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    if value.strip().isdigit():
        return float(value)
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        return None
    return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())


class RetryTransport(httpx.AsyncBaseTransport):
    """Retry idempotent requests that got 429 or 5xx. Non-idempotent methods are sent exactly once.

    Request bodies must be replayable (bytes or JSON, not a one-shot stream) for PUT retries.
    """

    def __init__(
        self,
        inner: httpx.AsyncBaseTransport,
        *,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.25,
        backoff_max_seconds: float = 5.0,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if max_attempts < 1:
            message = "max_attempts must be at least 1."
            raise ValueError(message)
        self._inner = inner
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base_seconds
        self._backoff_max = backoff_max_seconds
        self._sleep = sleep

    def _delay(self, attempt: int, response: httpx.Response) -> float:
        retry_after = _retry_after_seconds(response)
        if retry_after is not None:
            return min(retry_after, self._backoff_max)
        exponential = min(self._backoff_max, self._backoff_base * 2.0 ** (attempt - 1))
        return exponential * random.uniform(0.5, 1.0)  # noqa: S311 - jitter, not cryptography

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.method not in IDEMPOTENT_METHODS:
            return await self._inner.handle_async_request(request)

        attempt = 1
        while True:
            response = await self._inner.handle_async_request(request)
            if response.status_code not in RETRYABLE_STATUSES or attempt >= self._max_attempts:
                return response
            delay = self._delay(attempt, response)
            logger.warning(
                "http_retry",
                method=request.method,
                host=request.url.host,
                path=request.url.path,
                status=response.status_code,
                attempt=attempt,
                delay_seconds=round(delay, 3),
            )
            await response.aclose()
            await self._sleep(delay)
            attempt += 1

    async def aclose(self) -> None:
        await self._inner.aclose()


async def propagate_request_id(request: httpx.Request) -> None:
    request_id = current_request_id()
    if request_id is not None and REQUEST_ID_HEADER not in request.headers:
        request.headers[REQUEST_ID_HEADER] = request_id


def build_http_client(
    settings: BaseAppSettings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    sleep: Sleep = asyncio.sleep,
) -> httpx.AsyncClient:
    inner = transport or httpx.AsyncHTTPTransport(retries=settings.http_connect_retries)
    return httpx.AsyncClient(
        transport=RetryTransport(inner, max_attempts=settings.http_max_attempts, sleep=sleep),
        timeout=httpx.Timeout(
            settings.http_timeout_seconds,
            connect=settings.http_connect_timeout_seconds,
        ),
        event_hooks={"request": [propagate_request_id]},
        headers={"User-Agent": settings.app_name},
    )


def get_http_client(request: Request) -> httpx.AsyncClient:
    client: httpx.AsyncClient = request.app.state.http_client
    return client


HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
