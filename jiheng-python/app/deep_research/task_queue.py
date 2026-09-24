import json
import uuid


class TaskQueue:
    KEY = "task:queue:deep_research"

    def __init__(self, redis):
        self.redis = redis

    async def enqueue(self, payload: dict) -> str:
        task_id = str(uuid.uuid4())
        await self.redis.rpush(self.KEY, json.dumps({"task_id": task_id, **payload}, ensure_ascii=False))
        return task_id

    async def dequeue(self) -> dict | None:
        item = await self.redis.lpop(self.KEY)
        return json.loads(item) if item else None
