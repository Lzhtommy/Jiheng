import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, trace, world
from app.config import settings
from app.deep_research.runner import run_worker
from app.deep_research.task_queue import TaskQueue

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
    app.state.task_queue = TaskQueue()
    app.state.worker = asyncio.create_task(run_worker(app.state.task_queue))
    logger.info("app_started", app=settings.app_name)
    yield
    app.state.worker.cancel()
    logger.info("app_stopped", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(world.router, prefix="/chat/world", tags=["world"])
app.include_router(trace.router, prefix="/trace", tags=["trace"])


@app.get("/health")
async def health():
    return {"status": "ok"}
