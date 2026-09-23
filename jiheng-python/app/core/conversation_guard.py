from redis.asyncio import Redis


class ConversationGuard:
    """并发守卫（Redis 分布式锁）"""

    KEY_PREFIX = "chat:lock:"

    def __init__(self, redis: Redis):
        self.redis = redis

    async def acquire(self, conversation_id: str, ttl: int = 1800) -> bool:
        return await self.redis.set(self.KEY_PREFIX + conversation_id, "1", ex=ttl, nx=True)

    async def release(self, conversation_id: str):
        await self.redis.delete(self.KEY_PREFIX + conversation_id)
