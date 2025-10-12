import json
import logging
from typing import Dict, Set, Optional
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from realtime_messaging.models.notification import Notification, NotificationType
from realtime_messaging.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        # Store active WebSocket connections by user_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user's WebSocket for notifications."""
        # Don't accept here - it should be accepted by the endpoint before calling this

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        logger.info(
            f"User {user_id} connected to notification WebSocket. Total connections: {len(self.active_connections[user_id])}"
        )

        # Send initial unread notification count
        await self._send_unread_count(user_id)

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a user's WebSocket."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            logger.info(f"User {user_id} disconnected from notification WebSocket")

            # Clean up empty connection sets
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                logger.info(f"Removed empty connection set for user {user_id}")

    async def send_notification_to_user(self, user_id: str, notification_data: dict):
        """Send real-time notification to a specific user."""
        if user_id not in self.active_connections:
            logger.debug(f"User {user_id} not connected to WebSocket")
            return False

        disconnected = set()
        sent_count = 0

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "new_notification",
                            "data": notification_data,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            self.active_connections[user_id].discard(websocket)

        logger.info(f"Sent notification to {sent_count} connections for user {user_id}")
        return sent_count > 0

    async def send_notification_update(
        self, user_id: str, notification_id: str, status: str
    ):
        """Send notification status update to user."""
        if user_id not in self.active_connections:
            return False

        update_data = {
            "type": "notification_update",
            "data": {
                "notification_id": notification_id,
                "status": status,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        disconnected = set()
        sent_count = 0

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(json.dumps(update_data))
                sent_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to send notification update to user {user_id}: {e}"
                )
                disconnected.add(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            self.active_connections[user_id].discard(websocket)

        return sent_count > 0

    async def send_unread_count(self, user_id: str):
        """Public method to send unread count to user."""
        print(f"[NOTIFICATION_MANAGER] Sending unread count to user {user_id}")
        print(
            f"[NOTIFICATION_MANAGER] Active connections: {list(self.active_connections.keys())}"
        )
        print(
            f"[NOTIFICATION_MANAGER] User {user_id} in connections: {user_id in self.active_connections}"
        )
        await self._send_unread_count(user_id)

    async def _send_unread_count(self, user_id: str):
        """Send current unread notification count to user."""
        try:
            # This would need a database session - we'll implement this when we have session management
            # For now, just send a placeholder
            count_data = {
                "type": "unread_count",
                "data": {"count": 0},  # TODO: Get actual unread count from database
                "timestamp": datetime.utcnow().isoformat(),
            }

            print(f"[NOTIFICATION_MANAGER] Prepared count data: {count_data}")

            if user_id in self.active_connections:
                print(
                    f"[NOTIFICATION_MANAGER] Found {len(self.active_connections[user_id])} connections for user {user_id}"
                )
                for websocket in self.active_connections[user_id]:
                    try:
                        print(
                            f"[NOTIFICATION_MANAGER] Sending to websocket: {websocket}"
                        )
                        await websocket.send_text(json.dumps(count_data))
                        print(f"[NOTIFICATION_MANAGER] Successfully sent unread count")
                    except Exception as e:
                        logger.error(
                            f"Failed to send unread count to user {user_id}: {e}"
                        )
                        print(f"[NOTIFICATION_MANAGER] Error sending: {e}")
            else:
                print(
                    f"[NOTIFICATION_MANAGER] User {user_id} not in active connections!"
                )

        except Exception as e:
            logger.error(f"Failed to send unread count to user {user_id}: {e}")

    async def broadcast_to_room_participants(
        self, room_id: str, participant_ids: list, notification_data: dict
    ):
        """Broadcast notification to all participants in a room."""
        sent_count = 0

        for user_id in participant_ids:
            if await self.send_notification_to_user(str(user_id), notification_data):
                sent_count += 1

        logger.info(
            f"Broadcast notification to {sent_count}/{len(participant_ids)} users in room {room_id}"
        )
        return sent_count

    def get_connected_users(self) -> list:
        """Get list of currently connected user IDs."""
        return list(self.active_connections.keys())

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user is connected via WebSocket."""
        return (
            user_id in self.active_connections
            and len(self.active_connections[user_id]) > 0
        )


# Global notification manager instance
notification_manager = NotificationManager()
