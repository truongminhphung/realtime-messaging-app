from typing import List, Optional
from uuid import UUID as UUIDType
import json
import logging
from fastapi import HTTPException, status

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from realtime_messaging.models.chat_room import ChatRoom, ChatRoomCreate, ChatRoomGet
from realtime_messaging.models.room_participant import (
    RoomParticipant,
    RoomParticipantGet,
)
from realtime_messaging.models.user import User
from realtime_messaging.models.notification import (
    Notification,
    NotificationType,
    NotificationStatus,
)
from realtime_messaging.services.user_service import UserService
from realtime_messaging.config import settings
from realtime_messaging.exceptions import InternalServerError

# Redis client for caching
redis_client = redis.from_url(settings.redis_url)

logger = logging.getLogger(__name__)


class RoomService:
    """Service class for room management operations."""

    @staticmethod
    async def create_room(
        session: AsyncSession, room_data: ChatRoomCreate, creator_id: UUIDType
    ) -> ChatRoom:
        """Create a new chat room and add creator as first participant."""
        try:
            # Validate room name
            name = room_data.name.strip() if room_data.name else ""
            if not name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Room name cannot be empty",
                )

            if len(name) > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Room name must be 100 characters or less",
                )

            # Create the room
            room = ChatRoom(
                creator_id=creator_id,
                name=name,
                description=(
                    room_data.description.strip() if room_data.description else None
                ),
                is_private=room_data.is_private,
                max_participants=room_data.max_participants,
                avatar_url=room_data.avatar_url,
                settings=room_data.settings or {},
            )

            session.add(room)
            await session.flush()  # Get the room_id before committing

            # Add creator as first participant
            participant = RoomParticipant(room_id=room.room_id, user_id=creator_id)
            session.add(participant)

            await session.commit()
            await session.refresh(room)

            return room

        except IntegrityError as e:
            await session.rollback()
            logger.error(f"IntegrityError while creating room: {str(e)}")
            raise InternalServerError("Failed to create room due to database error")

    @staticmethod
    async def get_room(session: AsyncSession, room_id: UUIDType) -> Optional[ChatRoom]:
        """Get a room by ID."""
        stmt = select(ChatRoom).where(ChatRoom.room_id == room_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_rooms(
        session: AsyncSession, user_id: UUIDType
    ) -> List[ChatRoom]:
        """Get all rooms that a user is a participant in."""
        stmt = (
            select(ChatRoom)
            .join(RoomParticipant)
            .where(RoomParticipant.user_id == user_id)
            .order_by(ChatRoom.created_at.desc())
        )
        rooms = await session.execute(stmt)
        return rooms.scalars().all()

    @staticmethod
    async def is_user_participant(
        session: AsyncSession, room_id: UUIDType, user_id: UUIDType
    ) -> bool:
        """Check if a user is a participant in a room."""
        stmt = select(RoomParticipant).where(
            and_(RoomParticipant.room_id == room_id, RoomParticipant.user_id == user_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def join_room(
        session: AsyncSession, room_id: UUIDType, user_id: UUIDType
    ) -> bool:
        """Add a user to a room as a participant."""
        try:
            # Check if room exists
            room = await RoomService.get_room(session, room_id)
            if not room:
                raise ValueError("Room not found")

            # Check if user is already a participant
            if await RoomService.is_user_participant(session, room_id, user_id):
                return True  # Already a participant

            # Add user as participant
            participant = RoomParticipant(room_id=room_id, user_id=user_id)
            session.add(participant)
            await session.commit()

            # Clear cached participants for this room
            await redis_client.delete(f"room_participants:{room_id}")

            return True

        except IntegrityError as e:
            await session.rollback()
            # raise ValueError("Failed to join room")
            if "unique constraint failed" in str(e.orig):
                raise ValueError("User is already a participant")
            else:
                raise ValueError("Failed to join room due to database error")

    @staticmethod
    async def leave_room(
        session: AsyncSession, room_id: UUIDType, user_id: UUIDType
    ) -> bool:
        """Remove a user from a room."""
        try:
            # Check if user is a participant
            if not await RoomService.is_user_participant(session, room_id, user_id):
                return False

            # Remove participant
            stmt = delete(RoomParticipant).where(
                and_(
                    RoomParticipant.room_id == room_id,
                    RoomParticipant.user_id == user_id,
                )
            )
            result = await session.execute(stmt)
            await session.commit()

            # Clear cached participants for this room
            await redis_client.delete(f"room_participants:{room_id}")

            return result.rowcount > 0

        except Exception as e:
            await session.rollback()
            raise ValueError(f"Unexpected error while leaving room: {str(e)}")

    @staticmethod
    async def get_room_participants(
        session: AsyncSession, room_id: UUIDType, use_cache: bool = True
    ) -> List[dict]:
        """Get all participants in a room with their user details."""
        cache_key = f"room_participants:{room_id}"

        # Try to get from cache first
        if use_cache:
            cached = await redis_client.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError:
                    pass

        # Get from database
        stmt = (
            select(RoomParticipant, User)
            .join(User, RoomParticipant.user_id == User.user_id)
            .where(RoomParticipant.room_id == room_id)
            .order_by(RoomParticipant.joined_at.asc())
        )

        result = await session.execute(stmt)
        participants = []

        for participant, user in result.all():
            participant_data = {
                "user_id": str(user.user_id),
                "username": user.username,
                "display_name": user.display_name,
                "profile_picture_url": user.profile_picture_url,
                "joined_at": participant.joined_at.isoformat(),
            }
            participants.append(participant_data)

        # Cache the result for 5 minutes
        if use_cache and participants:
            await redis_client.setex(
                cache_key, 300, json.dumps(participants)  # 5 minutes
            )

        return participants

    @staticmethod
    async def invite_user_to_room(
        session: AsyncSession,
        room_id: UUIDType,
        inviter_id: UUIDType,
        invitee_email: str,
    ) -> bool:
        """Invite a user to a room by email and create a notification."""
        try:
            # Check if room exists and inviter is a participant
            room = await RoomService.get_room(session, room_id)
            if not room:
                raise ValueError("Room not found")

            if not await RoomService.is_user_participant(session, room_id, inviter_id):
                raise ValueError("You must be a participant to invite others")

            # Get invitee user by email
            invitee = await UserService.get_user_by_email(session, invitee_email)
            if not invitee:
                raise ValueError("User not found")

            # Check if invitee is already a participant
            if await RoomService.is_user_participant(session, room_id, invitee.user_id):
                raise ValueError("User is already a participant")

            # Get inviter details for the notification
            inviter = await UserService.get_user_by_id(session, inviter_id)

            # Create notification
            notification = Notification(
                user_id=invitee.user_id,
                type=NotificationType.ROOM_INVITATION,
                content=json.dumps(
                    {
                        "room_id": str(room_id),
                        "room_name": room.name,
                        "inviter_id": str(inviter_id),
                        "inviter_username": inviter.username if inviter else "Unknown",
                        "inviter_display_name": (
                            inviter.display_name if inviter else "Unknown User"
                        ),
                    }
                ),
                status=NotificationStatus.PENDING,
            )

            session.add(notification)
            await session.commit()

            # TODO: Publish to RabbitMQ for async processing
            # This would be implemented when we add the notification worker

            return True

        except ValueError:
            raise
        except Exception as e:
            await session.rollback()
            raise ValueError(f"Failed to send invitation: {str(e)}")

    @staticmethod
    async def get_room_with_participant_count(
        session: AsyncSession, room_id: UUIDType
    ) -> Optional[dict]:
        """Get room details with participant count."""
        room = await RoomService.get_room(session, room_id)
        if not room:
            return None

        # Count participants
        stmt = select(func.count(RoomParticipant.user_id)).where(
            RoomParticipant.room_id == room_id
        )
        result = await session.execute(stmt)
        participant_count = result.scalar() or 0

        return {
            "room_id": str(room.room_id),
            "name": room.name,
            "creator_id": str(room.creator_id),
            "created_at": room.created_at.isoformat(),
            "participant_count": participant_count,
        }

    @staticmethod
    async def update_room(
        session: AsyncSession, room_id: UUIDType, user_id: UUIDType, room_data: dict
    ) -> Optional[ChatRoom]:
        """Update room details (only creator can update)."""
        try:
            room = await RoomService.get_room(session, room_id)
            if not room:
                return None

            # Only creator can update room
            if room.creator_id != user_id:
                raise ValueError("Only room creator can update room details")

            # Update room name if provided
            if "name" in room_data and room_data["name"]:
                room.name = room_data["name"].strip()

            await session.commit()
            await session.refresh(room)

            return room

        except IntegrityError as e:
            await session.rollback()
            raise ValueError(f"Failed to update room due to database error: {str(e)}")
        except Exception as e:
            await session.rollback()
            raise ValueError(f"Unexpected error while updating room: {str(e)}")

    @staticmethod
    async def delete_room(
        session: AsyncSession, room_id: UUIDType, user_id: UUIDType
    ) -> bool:
        """Delete a room (only creator can delete)."""
        try:
            room = await RoomService.get_room(session, room_id)
            if not room:
                return False

            # Only creator can delete room
            if room.creator_id != user_id:
                raise ValueError("Only room creator can delete room")

            # Delete room (participants will be deleted due to CASCADE)
            await session.delete(room)
            await session.commit()

            # Clear cached data
            await redis_client.delete(f"room_participants:{room_id}")

            return True

        except Exception as e:
            await session.rollback()
            raise ValueError(f"Unexpected error while deleting room: {str(e)}")
