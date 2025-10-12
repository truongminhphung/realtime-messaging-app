from fastapi import (
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    status,
    Query,
)
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json

from realtime_messaging.websocket.notification_manager import notification_manager
from realtime_messaging.dependencies import get_database
from realtime_messaging.models.user import User
from realtime_messaging.services.auth import AuthService
from realtime_messaging.db.depends import get_db

logger = logging.getLogger(__name__)


async def websocket_notifications_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
):
    """WebSocket endpoint for real-time notifications with proper authentication."""

    user = None
    user_id = None

    try:
        # Accept the WebSocket connection first
        await websocket.accept()

        # Get database session and authenticate user
        async for session in get_db():
            # Debug logging
            logger.info(f"Attempting to authenticate with token: {token[:20]}...")

            # Authenticate user manually (can't use dependency injection with WebSocket)
            print(f"Token received: {token}")
            user = await AuthService.get_user_by_token(session, token)
            logger.info(f"Authentication result: {user is not None}")

            if user is None:
                logger.error("Authentication failed - user is None")
                await websocket.close(code=4001, reason="Invalid token")
                return

            user_id = str(user.user_id)
            await notification_manager.connect(websocket, user_id)
            logger.info(f"WebSocket connected for user {user_id} ({user.username})")

            try:
                while True:
                    # Keep connection alive and handle any incoming messages
                    data = await websocket.receive_text()
                    print(f"[DEBUG] Received data: {data}")
                    logger.info(f"Received WebSocket data: {data}")

                    try:
                        message = json.loads(data)
                        message_type = message.get("type", "")
                        print(f"[DEBUG] Parsed message type: '{message_type}'")
                        logger.info(f"Parsed message type: '{message_type}'")

                        if message_type == "ping":
                            print(f"[DEBUG] Sending pong response")
                            await websocket.send_text(json.dumps({"type": "pong"}))
                        elif message_type == "get_unread_count":
                            print(f"[DEBUG] Getting unread count for user {user_id}")
                            logger.info(f"Getting unread count for user {user_id}")
                            # Send current unread count
                            await notification_manager.send_unread_count(user_id)
                            print(f"[DEBUG] Sent unread count")
                        elif message_type == "mark_read":
                            # Handle marking notification as read
                            notification_id = message.get("notification_id")
                            if notification_id:
                                # TODO: Implement mark as read functionality
                                logger.info(
                                    f"User {user_id} marked notification {notification_id} as read"
                                )
                        else:
                            print(f"[DEBUG] Unknown message type: '{message_type}'")
                            logger.info(
                                f"Unknown message type from user {user_id}: '{message_type}'"
                            )
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "error",
                                        "message": f"Unknown message type: {message_type}",
                                    }
                                )
                            )

                    except json.JSONDecodeError as e:
                        # Handle legacy text messages
                        print(f"[DEBUG] JSON decode error: {e}, treating as plain text")
                        if data == "ping":
                            await websocket.send_text("pong")
                        else:
                            logger.debug(
                                f"Received text message from user {user_id}: {data}"
                            )
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "error",
                                        "message": "Invalid JSON format. Please send JSON messages.",
                                    }
                                )
                            )

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user_id}")
            except Exception as e:
                logger.error(f"WebSocket error for user {user_id}: {e}")
            finally:
                if user_id:
                    notification_manager.disconnect(websocket, user_id)

            break  # Exit the session loop

    except Exception as e:
        logger.error(f"WebSocket authentication/setup error: {e}")
        try:
            await websocket.close(code=4001, reason="Authentication failed")
        except:
            pass  # Connection might already be closed
