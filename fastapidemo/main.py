import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from api import data_api
from fastapidemo.utils import custom_openapi
from pagination import add_pagination
from response import ERROR, PARAM_ERROR
from response.exceptions import BizException

app = FastAPI(title="demo project")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/time")
async def gettime() -> int:
    return int(time.time())


@app.on_event("startup")
async def startup_event():
    ...


@app.on_event("shutdown")
async def shutdown_event():
    ...


@app.exception_handler(RequestValidationError)
async def handle_params_error(requset: Request, exc: RequestValidationError):
    detail = "; ".join([x["loc"][1] + ": " + x["msg"] for x in exc.errors()])
    return JSONResponse(jsonable_encoder(PARAM_ERROR(detail)))


@app.exception_handler(SQLAlchemyError)
async def handle_orm_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(jsonable_encoder(ERROR(exc)))


BizException.register(app)
app.include_router(data_api)
add_pagination(app)
app.openapi = custom_openapi(app)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=1)
