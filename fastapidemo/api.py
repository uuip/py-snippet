from fastapi import Query, Depends, Request, APIRouter
from sqlalchemy import select, update, insert, delete  # noqa
from sqlalchemy.ext.asyncio import AsyncSession

from db import async_session
from models import Detect, Ship
from pagination import Page, paginate
from response import OK, R
from schemas import DetectSchema, ShipSchema, Item

data_api = APIRouter(prefix="/dataset", tags=["查询数据集"])


@data_api.get("/detect/round", response_model=Page[DetectSchema], summary="查询轮次")
async def detect_round(s: AsyncSession = Depends(async_session), round: int = Query(ge=20)):
    qs = select(Detect).where(Detect.round == round)
    return await paginate(s, qs)


@data_api.get(
    "/ship/{token_id}",
    response_model=R[ShipSchema],
    response_model_by_alias=False,
    summary="查询Ship",
)
async def func2(token_id: int, s: AsyncSession = Depends(async_session)):
    qs = select(Ship).where(Ship.token_id == token_id)
    return OK(await s.scalar(qs))


@data_api.post("/index/")
async def index_post(request: Request, item: Item):
    # return JSONResponse(status_code=status.HTTP_201_CREATED, content=item)
    return item
