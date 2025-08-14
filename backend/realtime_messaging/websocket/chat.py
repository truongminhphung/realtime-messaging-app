import json
import asyncio
from typing import Dict, List, Set, Optional
from uuid import UUID as UUIDType
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ValidationError

from realtime_messaging.db.depends import sessionmanager
from realtime_messaging.models.message import (
    MessageCreateInternal,
    MessageWithSenderInfo,
)
from realtime_messaging.models.user import User
from realtime_messaging.services.message_service import MessageService
from realtime_messaging.services.room_service import RoomService
from realtime_messaging.services.auth import AuthService


router = APIRouter()


# WebSocket message types
class WSMessageType:
    """WebSocket message types for client-server communication."""

    # Client to server
    SEND_MESSAGE = "send_message"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"
    PING = "ping"

    # Server to client
    NEW_MESSAGE = "new_message"
    MESSAGE_SENT = "message_sent"
    MESSAGE_ERROR = "message_error"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_TYPING = "user_typing"
    USER_STOPPED_TYPING = "user_stopped_typing"
    PONG = "pong"
    ERROR = "error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


# Pydantic models for WebSocket messages
class WSMessage(BaseModel):
    type: str
    data: dict


class WSMessageSend(BaseModel):
    room_id: str
    content: str


class WSTypingEvent(BaseModel):
    room_id: str


# Connection manager for WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections for real-time messaging."""

    def __init__(self):
        # room_id -> set of connections
        self.room_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> user info
        self.connection_users: Dict[WebSocket, dict] = {}
        # room_id -> set of typing users
        self.typing_users: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user: User, room_id: str):
        """Accept WebSocket connection and add to room."""
        await websocket.accept()

        # Add to room connections
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        self.room_connections[room_id].add(websocket)

        # Store user info
        self.connection_users[websocket] = {
            "user_id": str(user.user_id),
            "username": user.username,
            "display_name": user.display_name,
            "room_id": room_id,
        }

        # Notify other users in room
        await self.broadcast_to_room(
            room_id,
            {
                "type": WSMessageType.USER_JOINED,
                "data": {
                    "user_id": str(user.user_id),
                    "username": user.username,
                    "display_name": user.display_name,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            },
            exclude=websocket,
        )

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.connection_users:
            user_info = self.connection_users[websocket]
            room_id = user_info["room_id"]
            user_id = user_info["user_id"]

            # Remove from room connections
            if room_id in self.room_connections:
                self.room_connections[room_id].discard(websocket)
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]

            # Remove from typing users
            if room_id in self.typing_users:
                self.typing_users[room_id].discard(user_id)
                if not self.typing_users[room_id]:
                    del self.typing_users[room_id]

            # Remove user info
            del self.connection_users[websocket]

            # Notify other users in room
            await self.broadcast_to_room(
                room_id,
                {
                    "type": WSMessageType.USER_LEFT,
                    "data": {
                        "user_id": user_id,
                        "username": user_info["username"],
                        "display_name": user_info["display_name"],
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                },
            )

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send message to specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception:
            # Connection might be closed
            await self.disconnect(websocket)

    async def broadcast_to_room(
        self, room_id: str, message: dict, exclude: Optional[WebSocket] = None
    ):
        """Broadcast message to all connections in a room."""
        if room_id not in self.room_connections:
            return

        # Create a copy of connections to avoid modification during iteration
        connections = self.room_connections[room_id].copy()

        for connection in connections:
            if connection != exclude:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    # Remove broken connections
                    await self.disconnect(connection)

    async def handle_typing_start(self, websocket: WebSocket, room_id: str):
        """Handle user started typing."""
        if websocket in self.connection_users:
            user_info = self.connection_users[websocket]
            user_id = user_info["user_id"]

            # Add to typing users
            if room_id not in self.typing_users:
                self.typing_users[room_id] = set()
            self.typing_users[room_id].add(user_id)

            # Notify other users
            await self.broadcast_to_room(
                room_id,
                {
                    "type": WSMessageType.USER_TYPING,
                    "data": {
                        "user_id": user_id,
                        "username": user_info["username"],
                        "display_name": user_info["display_name"],
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                },
                exclude=websocket,
            )

    async def handle_typing_stop(self, websocket: WebSocket, room_id: str):
        """Handle user stopped typing."""
        if websocket in self.connection_users:
            user_info = self.connection_users[websocket]
            user_id = user_info["user_id"]

            # Remove from typing users
            if room_id in self.typing_users:
                self.typing_users[room_id].discard(user_id)
                if not self.typing_users[room_id]:
                    del self.typing_users[room_id]

            # Notify other users
            await self.broadcast_to_room(
                room_id,
                {
                    "type": WSMessageType.USER_STOPPED_TYPING,
                    "data": {
                        "user_id": user_id,
                        "username": user_info["username"],
                        "display_name": user_info["display_name"],
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                },
                exclude=websocket,
            )

    def get_room_user_count(self, room_id: str) -> int:
        """Get number of connected users in a room."""
        return len(self.room_connections.get(room_id, set()))

    def get_typing_users(self, room_id: str) -> List[str]:
        """Get list of users currently typing in a room."""
        return list(self.typing_users.get(room_id, set()))


# Global connection manager
manager = ConnectionManager()


async def authenticate_websocket_user(token: str) -> Optional[User]:
    """Authenticate user from WebSocket token."""
    try:
        async for session in sessionmanager.get_session():
            user = await AuthService.get_user_by_token(session, token)
            return user
    except Exception:
        return None


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for real-time messaging."""
    user = None

    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required"
            )
            return

        # Authenticate user
        user = await authenticate_websocket_user(token)
        if not user:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication"
            )
            return

        # Validate room access
        room_uuid = UUIDType(room_id)
        async for session in sessionmanager.get_session():
            is_participant = await RoomService.is_user_participant(
                session, room_uuid, user.user_id
            )
            if not is_participant:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Not a room participant",
                )
                return
            break

        # Connect to room
        await manager.connect(websocket, user, room_id)

        # Send initial room info
        await manager.send_personal_message(
            websocket,
            {
                "type": "connected",
                "data": {
                    "room_id": room_id,
                    "user_id": str(user.user_id),
                    "connected_users": manager.get_room_user_count(room_id),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            },
        )

        # Message handling loop
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                ws_message = WSMessage(**message)

                # Handle different message types
                await handle_websocket_message(websocket, user, room_uuid, ws_message)

            except (json.JSONDecodeError, ValidationError) as e:
                await manager.send_personal_message(
                    websocket,
                    {
                        "type": WSMessageType.ERROR,
                        "data": {"error": "Invalid message format", "details": str(e)},
                    },
                )
            except Exception as e:
                await manager.send_personal_message(
                    websocket,
                    {
                        "type": WSMessageType.ERROR,
                        "data": {
                            "error": "Message processing failed",
                            "details": str(e),
                        },
                    },
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if user:
            await manager.disconnect(websocket)


async def handle_websocket_message(
    websocket: WebSocket, user: User, room_id: UUIDType, message: WSMessage
):
    """Handle different types of WebSocket messages."""

    if message.type == WSMessageType.SEND_MESSAGE:
        await handle_send_message(websocket, user, room_id, message.data)

    elif message.type == WSMessageType.TYPING_START:
        await manager.handle_typing_start(websocket, str(room_id))

    elif message.type == WSMessageType.TYPING_STOP:
        await manager.handle_typing_stop(websocket, str(room_id))

    elif message.type == WSMessageType.PING:
        await manager.send_personal_message(
            websocket,
            {
                "type": WSMessageType.PONG,
                "data": {"timestamp": datetime.utcnow().isoformat()},
            },
        )

    else:
        await manager.send_personal_message(
            websocket,
            {
                "type": WSMessageType.ERROR,
                "data": {"error": f"Unknown message type: {message.type}"},
            },
        )


async def handle_send_message(
    websocket: WebSocket, user: User, room_id: UUIDType, data: dict
):
    """Handle sending a message via WebSocket."""
    try:
        # Validate message data
        if "content" not in data or not data["content"].strip():
            await manager.send_personal_message(
                websocket,
                {
                    "type": WSMessageType.MESSAGE_ERROR,
                    "data": {"error": "Message content is required"},
                },
            )
            return

        # Check rate limit
        rate_limit_ok = await MessageService.check_rate_limit(user.user_id)
        if not rate_limit_ok:
            rate_info = await MessageService.get_rate_limit_info(user.user_id)
            await manager.send_personal_message(
                websocket,
                {
                    "type": WSMessageType.RATE_LIMIT_EXCEEDED,
                    "data": {
                        "error": "Rate limit exceeded",
                        "rate_limit_info": rate_info,
                    },
                },
            )
            return

        # Create message
        async for session in sessionmanager.get_session():
            message_data = MessageCreateInternal(
                room_id=room_id, sender_id=user.user_id, content=data["content"].strip()
            )

            message = await MessageService.create_message(session, message_data)

            # Get message with sender info
            messages = await MessageService.get_room_messages(
                session, room_id, limit=1, use_cache=False
            )

            if messages:
                message_with_info = messages[0]

                # Broadcast to all room participants
                await manager.broadcast_to_room(
                    str(room_id),
                    {
                        "type": WSMessageType.NEW_MESSAGE,
                        "data": message_with_info.model_dump(mode="json"),
                    },
                )

                # Send confirmation to sender
                await manager.send_personal_message(
                    websocket,
                    {
                        "type": WSMessageType.MESSAGE_SENT,
                        "data": {
                            "message_id": str(message.message_id),
                            "timestamp": message.created_at.isoformat(),
                        },
                    },
                )

                # Create notifications for other participants
                participants_data = await RoomService.get_room_participants(
                    session, room_id
                )
                participant_ids = [UUIDType(p["user_id"]) for p in participants_data]
                await MessageService.create_message_notification(
                    session, message, participant_ids
                )

            break

    except ValueError as e:
        await manager.send_personal_message(
            websocket, {"type": WSMessageType.MESSAGE_ERROR, "data": {"error": str(e)}}
        )
    except Exception as e:
        await manager.send_personal_message(
            websocket,
            {
                "type": WSMessageType.MESSAGE_ERROR,
                "data": {"error": "Failed to send message", "details": str(e)},
            },
        )


# Additional utility functions for WebSocket management
async def broadcast_message_to_room(room_id: UUIDType, message: MessageWithSenderInfo):
    """Broadcast a message to all WebSocket connections in a room."""
    await manager.broadcast_to_room(
        str(room_id),
        {"type": WSMessageType.NEW_MESSAGE, "data": message.model_dump(mode="json")},
    )


async def get_room_online_users(room_id: str) -> int:
    """Get number of online users in a room."""
    return manager.get_room_user_count(room_id)


async def get_room_typing_users(room_id: str) -> List[str]:
    """Get list of users currently typing in a room."""
    return manager.get_typing_users(room_id)
