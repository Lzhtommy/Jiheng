from redis.asyncio import Redis


class AbortManager:
    """中断管理"""

    KEY_PREFIX = "chat:abort:"

    def __init__(self, redis: Redis):
        self.redis = redis

    async def register(self, conversation_id: str):
        await self.redis.delete(self.KEY_PREFIX + conversation_id)

    async def is_aborted(self, conversation_id: str) -> bool:
        return await self.redis.exists(self.KEY_PREFIX + conversation_id) > 0

    async def abort(self, conversation_id: str):
        await self.redis.set(self.KEY_PREFIX + conversation_id, "1", ex=3600)
