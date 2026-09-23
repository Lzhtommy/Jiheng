import asyncio

from app.deep_research.task_queue import TaskQueue
from app.deep_research.worker import deep_research_worker


async def run_worker(redis) -> None:
    queue = TaskQueue(redis)
    while True:
        task = await queue.dequeue()
        if task is None:
            await asyncio.sleep(1)
            continue
        try:
            await deep_research_worker(task)
        except Exception:
            # The worker has already emitted a user-facing failure notification.
            continue
