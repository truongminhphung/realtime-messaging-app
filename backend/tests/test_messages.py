# import pytest
# from redis.asyncio import Redis
# from unittest.mock import AsyncMock

# pytestmark = pytest.mark.asyncio

# async def test_get_messages():
#     # Mock the Redis client
#     redis_mock = AsyncMock(spec=Redis)

#     message_data =b"test message"
#     timestamp = 1234567890
#     room_id = "uuid-1234"

#     await redis_mock.zadd(f"room:{room_id}:messages", {message_data:  timestamp})

#     await redis_mock.zadd.assert_called_once_with(
#         f"room:{room_id}:messages",
#         {message_data: timestamp}
#     )
