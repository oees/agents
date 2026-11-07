from typing import Annotated

import httpx
import pytest
from fastapi import Depends, FastAPI, Request
from sqlalchemy import func as sql_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import MAX_PAGE_SIZE, Page, PageParams, PageQuery, fetch_page

TOTAL = 120


@pytest.fixture
def numbers_route(app: FastAPI) -> FastAPI:
    @app.get("/numbers")
    async def numbers(
        request: Request,
        params: PageQuery,
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> Page[int]:
        series = sql_func.generate_series(1, TOTAL).table_valued("n").render_derived()
        statement = select(series.c.n).order_by(series.c.n)
        rows, count = await fetch_page(session, statement, params)
        return Page[int].build(request, params, rows, count)

    return app


@pytest.mark.usefixtures("numbers_route")
async def test_first_page_uses_the_default_size(client: httpx.AsyncClient) -> None:
    response = await client.get("/numbers")

    body = response.json()
    assert response.status_code == 200
    assert body["count"] == TOTAL
    assert body["results"] == list(range(1, 51))
    assert body["previous"] is None
    assert body["next"] == "http://testserver/numbers?page=2&page_size=50"


@pytest.mark.usefixtures("numbers_route")
async def test_middle_page_links_both_ways(client: httpx.AsyncClient) -> None:
    response = await client.get("/numbers", params={"page": 2, "page_size": 40})

    body = response.json()
    assert body["results"] == list(range(41, 81))
    assert body["previous"] == "http://testserver/numbers?page=1&page_size=40"
    assert body["next"] == "http://testserver/numbers?page=3&page_size=40"


@pytest.mark.usefixtures("numbers_route")
async def test_last_page_has_no_next(client: httpx.AsyncClient) -> None:
    response = await client.get("/numbers", params={"page": 3, "page_size": 50})

    body = response.json()
    assert body["results"] == list(range(101, 121))
    assert body["next"] is None


@pytest.mark.usefixtures("numbers_route")
@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page_size": 0}, {"page_size": MAX_PAGE_SIZE + 1}, {"unknown": "x"}],
)
async def test_out_of_range_params_are_validation_errors(
    client: httpx.AsyncClient, params: dict[str, int | str]
) -> None:
    response = await client.get("/numbers", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_offset_and_limit_follow_page_and_size() -> None:
    params = PageParams(page=3, page_size=25)

    assert (params.offset, params.limit) == (50, 25)
