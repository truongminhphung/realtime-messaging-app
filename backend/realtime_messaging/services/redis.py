from redis.asyncio import Redis

redis = Redis.from_url("redis://localhost:6379", decode_responses=True)
async def get_redis() -> Redis:
    return redis

