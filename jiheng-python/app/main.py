import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from redis.asyncio import Redis

from app.api import chat, trace
from app.config import settings
from app.deep_research.runner import run_worker

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        db=settings.redis_db,
        decode_responses=True,
    )
    app.state.worker = asyncio.create_task(run_worker(app.state.redis))
    logger.info("app_started", app=settings.app_name)
    yield
    app.state.worker.cancel()
    await app.state.redis.close()
    logger.info("app_stopped", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(trace.router, prefix="/trace", tags=["trace"])


@app.get("/health")
async def health():
    return {"status": "ok"}
