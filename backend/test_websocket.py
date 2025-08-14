#!/usr/bin/env python3
"""
Test script for WebSocket functionality.
This script demonstrates how to test the real-time messaging features.
"""

import asyncio
import json
import websockets
import requests
from uuid import uuid4


# Configuration
API_BASE_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"


async def test_websocket_connection():
    """Test WebSocket connection and messaging."""

    print("🚀 Testing WebSocket Real-time Messaging")
    print("=" * 50)

    # Step 1: Create test users and authenticate
    print("1. Creating test users...")

    # Create user 1
    user1_data = {
        "username": f"testuser1_{uuid4().hex[:8]}",
        "email": f"test1_{uuid4().hex[:8]}@example.com",
        "password": "testpass123",
    }

    # Create user 2
    user2_data = {
        "username": f"testuser2_{uuid4().hex[:8]}",
        "email": f"test2_{uuid4().hex[:8]}@example.com",
        "password": "testpass123",
    }

    # Register users
    response1 = requests.post(f"{API_BASE_URL}/auth/register", json=user1_data)
    response2 = requests.post(f"{API_BASE_URL}/auth/register", json=user2_data)

    if response1.status_code != 201 or response2.status_code != 201:
        print("❌ Failed to create users")
        return

    print(f"✅ Created users: {user1_data['username']} and {user2_data['username']}")

    # Step 2: Login and get tokens
    print("2. Logging in...")

    login1 = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": user1_data["username"], "password": user1_data["password"]},
    )

    login2 = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": user2_data["username"], "password": user2_data["password"]},
    )

    if login1.status_code != 200 or login2.status_code != 200:
        print("❌ Failed to login users")
        return

    token1 = login1.json()["access_token"]
    token2 = login2.json()["access_token"]

    print("✅ Users logged in successfully")

    # Step 3: Create a chat room
    print("3. Creating a chat room...")

    room_data = {
        "name": f"Test Room {uuid4().hex[:8]}",
        "description": "WebSocket test room",
    }

    room_response = requests.post(
        f"{API_BASE_URL}/rooms",
        json=room_data,
        headers={"Authorization": f"Bearer {token1}"},
    )

    if room_response.status_code != 201:
        print("❌ Failed to create room")
        return

    room_id = room_response.json()["room_id"]
    print(f"✅ Created room: {room_id}")

    # Step 4: Add user2 to the room
    print("4. Adding second user to room...")

    invite_response = requests.post(
        f"{API_BASE_URL}/rooms/{room_id}/invite",
        json={"username": user2_data["username"]},
        headers={"Authorization": f"Bearer {token1}"},
    )

    if invite_response.status_code != 200:
        print("❌ Failed to invite user to room")
        return

    print("✅ User2 added to room")

    # Step 5: Connect to WebSocket
    print("5. Connecting to WebSocket...")

    async def user1_connection():
        """Handle user1 WebSocket connection."""
        uri = f"{WS_BASE_URL}/ws/{room_id}?token={token1}"

        try:
            async with websockets.connect(uri) as websocket:
                print(f"🔗 User1 connected to WebSocket")

                # Listen for messages
                async for message in websocket:
                    data = json.loads(message)
                    print(f"📥 User1 received: {data['type']} - {data.get('data', {})}")

                    # Send a test message after connection
                    if data["type"] == "connected":
                        test_message = {
                            "type": "send_message",
                            "data": {"content": "Hello from User1! 👋"},
                        }
                        await websocket.send(json.dumps(test_message))
                        print("📤 User1 sent message")

                        # Wait a bit then send another message
                        await asyncio.sleep(2)
                        test_message2 = {
                            "type": "send_message",
                            "data": {"content": "This is a real-time message! 🚀"},
                        }
                        await websocket.send(json.dumps(test_message2))
                        print("📤 User1 sent second message")

        except Exception as e:
            print(f"❌ User1 WebSocket error: {e}")

    async def user2_connection():
        """Handle user2 WebSocket connection."""
        # Wait a moment before connecting
        await asyncio.sleep(1)

        uri = f"{WS_BASE_URL}/ws/{room_id}?token={token2}"

        try:
            async with websockets.connect(uri) as websocket:
                print(f"🔗 User2 connected to WebSocket")

                # Listen for messages
                message_count = 0
                async for message in websocket:
                    data = json.loads(message)
                    print(f"📥 User2 received: {data['type']} - {data.get('data', {})}")

                    # Respond to first new message
                    if data["type"] == "new_message" and message_count == 0:
                        message_count += 1
                        await asyncio.sleep(1)

                        response_message = {
                            "type": "send_message",
                            "data": {"content": "Hello back from User2! 👍"},
                        }
                        await websocket.send(json.dumps(response_message))
                        print("📤 User2 sent response")

                        # Test typing indicators
                        await asyncio.sleep(1)
                        await websocket.send(
                            json.dumps({"type": "typing_start", "data": {}})
                        )
                        print("⌨️ User2 started typing")

                        await asyncio.sleep(2)
                        await websocket.send(
                            json.dumps({"type": "typing_stop", "data": {}})
                        )
                        print("⌨️ User2 stopped typing")

        except Exception as e:
            print(f"❌ User2 WebSocket error: {e}")

    # Step 6: Run both connections concurrently
    print("6. Testing real-time messaging...")

    try:
        await asyncio.gather(
            asyncio.wait_for(user1_connection(), timeout=15),
            asyncio.wait_for(user2_connection(), timeout=15),
        )
    except asyncio.TimeoutError:
        print("⏱️ Test completed (timeout reached)")
    except Exception as e:
        print(f"❌ Test error: {e}")

    print("\n🎉 WebSocket test completed!")
    print("=" * 50)


def test_rate_limiting():
    """Test rate limiting functionality."""
    print("\n📊 Testing Rate Limiting")
    print("-" * 30)

    # This would require rapid message sending to test rate limits
    print("Rate limiting test would require sending >10 messages/minute")
    print("This can be tested manually through the frontend interface")


def main():
    """Run all tests."""
    print("🧪 Real-time Messaging WebSocket Tests")
    print("======================================")
    print("Make sure the backend server is running on localhost:8000")
    print("Press Ctrl+C to stop the test\n")

    try:
        asyncio.run(test_websocket_connection())
        test_rate_limiting()
    except KeyboardInterrupt:
        print("\n⛔ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    main()
