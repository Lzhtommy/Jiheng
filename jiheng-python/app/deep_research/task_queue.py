import asyncio
import uuid


class TaskQueue:
    """进程内深度研究队列，重启后未执行的任务会丢失"""

    def __init__(self):
        self._queue: asyncio.Queue[dict] = asyncio.Queue()

    async def enqueue(self, payload: dict) -> str:
        task_id = str(uuid.uuid4())
        await self._queue.put({"task_id": task_id, **payload})
        return task_id

    async def dequeue(self) -> dict:
        return await self._queue.get()
