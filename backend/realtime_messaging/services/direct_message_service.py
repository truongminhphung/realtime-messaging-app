from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID as UUIDType
from datetime import datetime, timezone

from realtime_messaging.models.direct_messages import DirectMessageRoomInfo
from realtime_messaging.models.chat_room import ChatRoom, ChatRoomCreate
from realtime_messaging.models.room_participant import RoomParticipant
from realtime_messaging.models.user import User
from realtime_messaging.models.userprofile import UserProfile
from realtime_messaging.models.message import Message
from realtime_messaging.services.room_service import RoomService


async def get_user_dm_conversations(
    session: AsyncSession, user_id: UUIDType
) -> list[DirectMessageRoomInfo]:
    """
    Retrieve all direct message conversations for the specified user.
    Returns a list of DirectMessageRoomInfo sorted by most recent message.
    """
    stmt = (
        select(ChatRoom)
        .join(RoomParticipant, ChatRoom.room_id == RoomParticipant.room_id)
        .where(
            and_(
                RoomParticipant.user_id == user_id,
                ChatRoom.is_direct_message == True,
            )
        )
    )
    result = await session.execute(stmt)
    dm_rooms = result.scalars().all()

    conversations = []

    for room in dm_rooms:
        other_user = await _get_other_user_info(session, room.room_id, user_id)
        if not other_user:
            continue

        last_message = await _get_last_message_in_room(session, room.room_id)

        # TODO: Get unread count (requires message read tracking)
        # TODO: Get online status (requires WebSocket connection tracking)
        conversation = DirectMessageRoomInfo(
            room_id=room.room_id,
            other_user_id=other_user["user_id"],
            other_username=other_user["username"],
            other_display_name=other_user["display_name"],
            other_profile_picture_url=other_user["profile_picture_url"],
            is_online=False,  # Placeholder
            last_message=last_message.content if last_message else None,
            last_message_at=last_message.created_at if last_message else None,
            unread_count=0,  # Placeholder
        )
        conversations.append(conversation)

    # Sort by last message time (most recent first), fallback to room creation time
    conversations.sort(
        key=lambda x: (
            x.last_message_at
            if x.last_message_at
            else datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )
    return conversations


async def get_or_create_dm_room(
    session: AsyncSession, user1_id: UUIDType, user2_id: UUIDType
) -> ChatRoom:
    """
    Get an existing direct message room between two users, or create one if it doesn't exist.
    """
    if user1_id == user2_id:
        raise ValueError("Cannot start a direct message conversation with yourself.")

    # Sort UUIDs to ensure consistent room name
    ids = sorted([str(user1_id), str(user2_id)])
    dm_room_name = f"dm_{ids[0]}_{ids[1]}"

    # Check if room already exists
    stmt = select(ChatRoom).where(
        and_(
            ChatRoom.name == dm_room_name,
            ChatRoom.is_direct_message == True,
        )
    )
    result = await session.execute(stmt)
    existing_room = result.scalar_one_or_none()
    print(f"\nexisting_room: {existing_room.room_id}")
    if existing_room:
        return existing_room

    # Create new DM room
    room = ChatRoomCreate(
        name=dm_room_name,
        is_private=True,
        is_direct_message=True,
        max_participants=2,
        description="Direct Message Room",
    )

    room = await RoomService.create_room(session, room, creator_id=user1_id)

    # Add both users as participants
    if user1_id != user2_id:
        await RoomService.join_room(session, room.room_id, user2_id)

    return room


async def _get_last_message_in_room(
    session: AsyncSession, room_id: UUIDType
) -> Message | None:
    """Get the most recent message in a room."""
    stmt = (
        select(Message)
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_other_user_info(
    session: AsyncSession, room_id: UUIDType, current_user_id: UUIDType
) -> dict[str, any] | None:
    """Get information about the other user in a direct message room."""
    stmt = (
        select(
            User.user_id,
            User.username,
            User.display_name,
            UserProfile.profile_picture_url,
        )
        .join(RoomParticipant, RoomParticipant.user_id == User.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.user_id)
        .where(
            and_(
                RoomParticipant.room_id == room_id,
                RoomParticipant.user_id != current_user_id,
            )
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return {
        "user_id": row.user_id,
        "username": row.username,
        "display_name": row.display_name,
        "profile_picture_url": row.profile_picture_url,
    }
