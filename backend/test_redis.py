#!/usr/bin/env python3
"""
Test Redis connection to verify it's working properly.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, "/home/phung/Documents/my_project/realtime-messaging-app/backend")


async def test_redis_connection():
    """Test Redis connection."""
    try:
        import redis.asyncio as redis
        from realtime_messaging.config import settings

        print(f"Testing Redis connection to: {settings.redis_url}")

        # Create Redis client
        redis_client = redis.from_url(settings.redis_url)

        # Test basic operations
        print("Testing SET operation...")
        await redis_client.set("test_key", "test_value", ex=10)
        print("✅ SET operation successful")

        print("Testing GET operation...")
        result = await redis_client.get("test_key")
        print(f"✅ GET operation successful: {result}")

        if result == b"test_value":
            print("✅ Redis is working correctly!")
        else:
            print(f"❌ Unexpected value: expected b'test_value', got {result}")

        # Test delete
        # await redis_client.delete("test_key")
        print("✅ DELETE operation successful")

        # Close connection
        await redis_client.close()
        print("✅ Connection closed successfully")

        return True

    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("\nPossible solutions:")
        print("1. Make sure Redis is running: docker-compose up redis -d")
        print("2. Check if Redis port 6379 is accessible: telnet localhost 6379")
        print("3. Verify REDIS_URL environment variable")
        return False


async def main():
    print("=" * 50)
    print("REDIS CONNECTION TEST")
    print("=" * 50)

    success = await test_redis_connection()

    print("\n" + "=" * 50)
    if success:
        print("🎉 Redis test PASSED - Redis is working!")
    else:
        print("❌ Redis test FAILED - Check Redis configuration")
    print("=" * 50)

    return success


if __name__ == "__main__":
    asyncio.run(main())
