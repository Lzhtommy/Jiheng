import asyncio

import structlog

from app.config import settings
from app.deep_research.progress_notifier import ProgressNotifier
from app.deep_research.task_queue import TaskQueue
from app.deep_research.worker import deep_research_worker

logger = structlog.get_logger()


async def run_worker(queue: TaskQueue) -> None:
    while True:
        task = await queue.dequeue()
        try:
            async with asyncio.timeout(settings.deep_research_timeout_seconds):
                await deep_research_worker(task)
        except TimeoutError:
            logger.warning("deep_research_timeout", task_id=task.get("task_id"))
            try:
                await ProgressNotifier().notify(task["user_id"], task["task_id"], "研究超时，请稍后重试")
            except Exception:
                logger.warning("deep_research_timeout_notify_failed", task_id=task.get("task_id"))
        except Exception:
            # The worker has already emitted a user-facing failure notification.
            continue
