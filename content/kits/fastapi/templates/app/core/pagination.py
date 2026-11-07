"""Page-number pagination with the shared response shape.

    {"count": 120, "next": "https://.../items?page=3&page_size=50", "previous": "...",
     "results": [...]}

Routers take `PageQuery`, repositories call `fetch_page`, and the router returns `Page.build(...)`.
"""

from collections.abc import Sequence
from typing import Annotated, Self

from fastapi import Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


class PageParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


PageQuery = Annotated[PageParams, Query()]


class Page[T](BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[T]

    @classmethod
    def build(cls, request: Request, params: PageParams, results: Sequence[T], count: int) -> Self:
        def link(page: int) -> str:
            return str(request.url.include_query_params(page=page, page_size=params.page_size))

        has_next = params.offset + len(results) < count
        return cls(
            count=count,
            next=link(params.page + 1) if has_next else None,
            previous=link(params.page - 1) if params.page > 1 else None,
            results=list(results),
        )


async def fetch_page[R](
    session: AsyncSession, statement: Select[R], params: PageParams
) -> tuple[Sequence[R], int]:
    """One page of `statement` plus the total count. `statement` needs a deterministic order_by."""
    count_statement: Select[int] = select(func.count()).select_from(
        statement.order_by(None).subquery()
    )
    count = await session.scalar(count_statement)
    rows = await session.scalars(statement.limit(params.limit).offset(params.offset))
    return rows.all(), count or 0


__all__ = ["DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE", "Page", "PageParams", "PageQuery", "fetch_page"]
