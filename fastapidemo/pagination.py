from typing import TypeVar, Generic, Sequence

from fastapi import Query
from fastapi_pagination import add_pagination, LimitOffsetPage  # noqa
from fastapi_pagination.bases import AbstractPage
from fastapi_pagination.default import Params as BaseParams
from fastapi_pagination.ext.async_sqlalchemy import paginate  # noqa
from pydantic import conint

T = TypeVar("T")


class Params(BaseParams):
    size: int = Query(10, ge=1, description="Page size")


class Page(AbstractPage[T], Generic[T]):
    code: int = 200
    page: conint(ge=1)  # type: ignore
    size: conint(ge=1)  # type: ignore
    total: conint(ge=0)
    data: Sequence[T]
    __params_type__ = Params

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        params: Params,
    ) -> "Page[T]":
        return cls(
            total=total,
            data=items,
            page=params.page,
            size=params.size,
        )
