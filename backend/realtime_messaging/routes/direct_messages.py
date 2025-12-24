from uuid import UUID as UUIDType
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from realtime_messaging.exceptions import InternalServerError
from realtime_messaging.db.depends import get_db
from realtime_messaging.dependencies import CurrentUser
from realtime_messaging.models.direct_messages import (
    DirectMessageInitiate,
    DirectMessageRoomInfo,
)
from realtime_messaging.models.message import MessageGet, MessageCreate
from realtime_messaging.services.direct_message_service import (
    get_user_dm_conversations,
    get_or_create_dm_room,
)
from realtime_messaging.services.message_service import MessageService

router = APIRouter(prefix="/direct-messages", tags=["direct-messages"])


@router.get("/", response_model=list[DirectMessageRoomInfo])
async def get_dm_conversations(
    current_user: CurrentUser, session: AsyncSession = Depends(get_db)
):
    """
    Get all direct message conversations for the current user.
    Returns list sorted by most recent message.
    """
    conversations = await get_user_dm_conversations(session, current_user.user_id)
    return conversations


@router.post("/", response_model=DirectMessageRoomInfo)
async def initiate_dm_conversation(
    dm_request: DirectMessageInitiate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> DirectMessageRoomInfo:
    """
    Start a direct message conversation with another user.
    If conversation already exists, returns existing one.
    """
    # get or create the DM room and return its info
    room = await get_or_create_dm_room(
        session, current_user.user_id, dm_request.other_user_id
    )
    print(f"DM room ID: {room.room_id}")

    # Get conversation info
    conversations = await get_user_dm_conversations(session, current_user.user_id)

    # Find and return the conversation we just created/returned
    for cs in conversations:
        if cs.room_id == room.room_id:
            return cs

    raise InternalServerError("Failed to retrieve direct message conversation info.")


@router.get("/{user_id}/messages", response_model=list[MessageGet])
async def get_dm_messages(
    user_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> list[MessageGet]:
    """
    Get message history in a direct message conversation with the specified user.
    Supports pagination via limit and offset.
    """
    room = await get_or_create_dm_room(session, current_user.user_id, user_id)
    # get meesages from that room
    messages = await MessageService.get_room_messages(
        session, room.room_id, limit, offset
    )
    return [MessageGet.model_validate(msg) for msg in messages]


@router.post(
    "/{user_id}/messages",
    response_model=MessageGet,
    status_code=status.HTTP_201_CREATED,
)
async def send_dm_message(
    user_id: UUIDType,
    message_content: MessageCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> MessageGet:
    """
    Send a direct message to a user.
    """
    # Get or create the DM room
    room = await get_or_create_dm_room(session, current_user.user_id, user_id)

    message_content.room_id = room.room_id
    message_content.sender_id = current_user.user_id

    message = await MessageService.create_message(session, message_content)
    return message
