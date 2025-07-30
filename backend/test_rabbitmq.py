#!/usr/bin/env python3
"""
Test script for RabbitMQ message notification system.
This script demonstrates the async notification processing workflow.
"""

import asyncio
import json
import logging
from uuid import uuid4, UUID as UUIDType

from realtime_messaging.services.rabbitmq import (
    rabbitmq_service,
    publish_message_notification,
)
from realtime_messaging.services.notification_worker import notification_worker


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_rabbitmq_notifications():
    """Test the complete RabbitMQ notification workflow."""

    print("🐰 Testing RabbitMQ Message Notifications")
    print("=" * 50)

    try:
        # Step 1: Connect to RabbitMQ
        print("1. Connecting to RabbitMQ...")
        await rabbitmq_service.connect()
        print("✅ Connected to RabbitMQ successfully")

        # Step 2: Test message publishing
        print("\n2. Publishing test notifications...")

        # Create test data
        message_id = uuid4()
        room_id = uuid4()
        sender_id = uuid4()
        recipient_ids = [uuid4(), uuid4(), uuid4()]

        sender_info = {
            "user_id": str(sender_id),
            "username": "test_sender",
            "display_name": "Test Sender",
            "profile_picture_url": None,
        }

        # Publish notification
        success = await publish_message_notification(
            message_id=message_id,
            room_id=room_id,
            sender_id=sender_id,
            recipient_ids=recipient_ids,
            message_content="This is a test message for RabbitMQ notifications! 🚀",
            sender_info=sender_info,
        )

        if success:
            print("✅ Successfully published notification to RabbitMQ")
        else:
            print("❌ Failed to publish notification")
            return

        # Step 3: Test direct message processing
        print("\n3. Testing notification processing...")

        # Create test notification data
        test_notification = {
            "type": "new_message",
            "message_id": str(message_id),
            "room_id": str(room_id),
            "sender_id": str(sender_id),
            "recipient_ids": [str(rid) for rid in recipient_ids],
            "message_content": "Test message content",
            "sender_info": sender_info,
            "timestamp": "2025-01-27T12:00:00Z",
            "retry_count": 0,
        }

        # Process the notification directly
        result = await notification_worker.process_notification(test_notification)

        if result:
            print("✅ Successfully processed notification")
        else:
            print("❌ Failed to process notification")

        # Step 4: Test queue health
        print("\n4. Testing queue health...")

        health_ok = await rabbitmq_service.health_check()
        if health_ok:
            print("✅ RabbitMQ health check passed")
        else:
            print("❌ RabbitMQ health check failed")

        # Step 5: Test error handling
        print("\n5. Testing error handling...")

        # Test with malformed data
        malformed_notification = {
            "type": "new_message",
            "invalid_field": "this should fail",
        }

        error_result = await notification_worker.process_notification(
            malformed_notification
        )
        if error_result:
            print("✅ Error handling working (malformed data handled gracefully)")
        else:
            print("❌ Error handling needs improvement")

        print("\n🎉 RabbitMQ notification tests completed!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error(f"Test error: {e}")

    finally:
        # Cleanup
        print("\n6. Cleaning up...")
        await rabbitmq_service.disconnect()
        print("✅ Disconnected from RabbitMQ")


async def test_queue_performance():
    """Test queue performance with multiple messages."""

    print("\n📊 Testing Queue Performance")
    print("-" * 30)

    try:
        await rabbitmq_service.connect()

        # Send multiple messages quickly
        start_time = asyncio.get_event_loop().time()

        tasks = []
        for i in range(10):
            task = publish_message_notification(
                message_id=uuid4(),
                room_id=uuid4(),
                sender_id=uuid4(),
                recipient_ids=[uuid4()],
                message_content=f"Performance test message {i}",
                sender_info={
                    "user_id": str(uuid4()),
                    "username": f"user_{i}",
                    "display_name": f"User {i}",
                    "profile_picture_url": None,
                },
            )
            tasks.append(task)

        # Execute all tasks
        results = await asyncio.gather(*tasks)

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        success_count = sum(1 for r in results if r)

        print(f"📈 Performance Results:")
        print(f"   • Messages sent: {len(tasks)}")
        print(f"   • Successful: {success_count}")
        print(f"   • Failed: {len(tasks) - success_count}")
        print(f"   • Duration: {duration:.3f} seconds")
        print(f"   • Rate: {len(tasks) / duration:.1f} messages/second")

    except Exception as e:
        print(f"❌ Performance test failed: {e}")

    finally:
        await rabbitmq_service.disconnect()


async def test_worker_resilience():
    """Test worker resilience to various error conditions."""

    print("\n🛡️ Testing Worker Resilience")
    print("-" * 30)

    # Test cases with different error conditions
    test_cases = [
        {"name": "Empty message", "data": {}},
        {
            "name": "Unknown message type",
            "data": {"type": "unknown_type", "data": "test"},
        },
        {
            "name": "Missing required fields",
            "data": {
                "type": "new_message",
                "message_id": str(uuid4()),
                # Missing other required fields
            },
        },
        {
            "name": "Invalid UUID format",
            "data": {
                "type": "new_message",
                "message_id": "invalid-uuid",
                "room_id": str(uuid4()),
                "sender_id": str(uuid4()),
                "recipient_ids": ["also-invalid-uuid"],
                "message_content": "test",
                "sender_info": {},
            },
        },
        {
            "name": "Valid message",
            "data": {
                "type": "new_message",
                "message_id": str(uuid4()),
                "room_id": str(uuid4()),
                "sender_id": str(uuid4()),
                "recipient_ids": [str(uuid4())],
                "message_content": "Valid test message",
                "sender_info": {
                    "user_id": str(uuid4()),
                    "username": "test_user",
                    "display_name": "Test User",
                },
            },
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. Testing: {test_case['name']}")

        try:
            result = await notification_worker.process_notification(test_case["data"])
            status = "✅ Handled" if result else "⚠️ Rejected"
            print(f"   {status}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

    print("🛡️ Resilience testing completed")


def main():
    """Run all RabbitMQ tests."""
    print("🧪 RabbitMQ Message Notification Tests")
    print("======================================")
    print("Make sure RabbitMQ is running on localhost:5672")
    print("Press Ctrl+C to stop the tests\n")

    try:
        asyncio.run(test_rabbitmq_notifications())
        asyncio.run(test_queue_performance())
        asyncio.run(test_worker_resilience())
    except KeyboardInterrupt:
        print("\n⛔ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")


if __name__ == "__main__":
    main()
