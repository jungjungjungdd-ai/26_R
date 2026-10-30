from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import init_db
from .errors import ApiError, api_error_handler, internal_error_handler
from .routers import findings, live, logs, runs, system



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # 서버가 켜질 때 분석 결과 테이블 생성
    yield


app = FastAPI(title="Shadow AI Radar API", version="0.1.0", lifespan=lifespan)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(Exception, internal_error_handler)

app.include_router(system.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(live.router, prefix="/api")
