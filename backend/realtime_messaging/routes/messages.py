from typing import List, Optional
from uuid import UUID as UUIDType

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from realtime_messaging.db.depends import get_db
from realtime_messaging.models.message import MessageCreate, MessageCreateInternal, MessageGet, MessageWithSenderInfo, MessageUpdate
from realtime_messaging.services.message_service import MessageService
from realtime_messaging.services.room_service import RoomService
from realtime_messaging.dependencies import CurrentUser


router = APIRouter(prefix="/messages", tags=["messages"])


# Additional Pydantic models for responses
class MessageCreateResponse(BaseModel):
    message: MessageWithSenderInfo
    rate_limit_info: dict


class RateLimitInfo(BaseModel):
    messages_sent: int
    messages_remaining: int
    reset_in_seconds: int
    limit: int


class MessageSearchRequest(BaseModel):
    query: str


# Message CRUD endpoints
@router.post("/", response_model=MessageCreateResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message_data: MessageCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> MessageCreateResponse:
    """Send a message to a room."""
    try:
        # Validate user is participant in the room
        is_participant = await MessageService.validate_message_access(
            session, message_data.room_id, current_user.user_id
        )
        
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a participant in the room to send messages"
            )
        
        # Check rate limit
        rate_limit_ok = await MessageService.check_rate_limit(current_user.user_id)
        if not rate_limit_ok:
            rate_info = await MessageService.get_rate_limit_info(current_user.user_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {rate_info['reset_in_seconds']} seconds"
            )
        
        # Create internal message data with sender_id
        internal_message_data = MessageCreateInternal(
            room_id=message_data.room_id,
            sender_id=current_user.user_id,
            content=message_data.content
        )
        
        # Create message
        message = await MessageService.create_message(session, internal_message_data)
        
        # Get message with sender info
        messages = await MessageService.get_room_messages(
            session, message_data.room_id, limit=1, use_cache=False
        )
        
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created message"
            )
        
        # Get updated rate limit info
        rate_limit_info = await MessageService.get_rate_limit_info(current_user.user_id)
        
        # Create notifications for other participants
        participants_data = await RoomService.get_room_participants(session, message_data.room_id)
        participant_ids = [UUIDType(p["user_id"]) for p in participants_data]
        await MessageService.create_message_notification(session, message, participant_ids)
        
        return MessageCreateResponse(
            message=messages[0],  # Most recent message (the one we just created)
            rate_limit_info=rate_limit_info
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/rooms/{room_id}", response_model=List[MessageWithSenderInfo])
async def get_room_messages(
    room_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100, ge=1, description="Number of messages to retrieve")
) -> List[MessageWithSenderInfo]:
    """Get recent messages for a room."""
    try:
        # Validate user is participant in the room
        is_participant = await MessageService.validate_message_access(
            session, room_id, current_user.user_id
        )
        
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a participant in the room to view messages"
            )
        
        # Get messages
        messages = await MessageService.get_room_messages(session, room_id, limit=limit)
        return messages
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )


@router.get("/{message_id}", response_model=MessageWithSenderInfo)
async def get_message(
    message_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> MessageWithSenderInfo:
    """Get a specific message by ID."""
    try:
        # Get the message first to check room access
        message = await MessageService.get_message_by_id(session, message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Validate user is participant in the room
        is_participant = await MessageService.validate_message_access(
            session, message.room_id, current_user.user_id
        )
        
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a participant in the room to view this message"
            )
        
        # Get message with sender info
        messages = await MessageService.get_room_messages(session, message.room_id, limit=1000, use_cache=False)
        
        # Find the specific message
        for msg in messages:
            if msg.message_id == message_id:
                return msg
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve message"
        )


@router.put("/{message_id}", response_model=MessageWithSenderInfo)
async def update_message(
    message_id: UUIDType,
    message_data: MessageUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> MessageWithSenderInfo:
    """Update a message (only sender can update)."""
    try:
        # Pydantic validation in MessageUpdate model handles content validation
        if not message_data.content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content is required for message update"
            )
        
        # Update message (content validation handled by Pydantic)
        updated_message = await MessageService.update_message(
            session, message_id, current_user.user_id, message_data.content
        )
        
        if not updated_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Get updated message with sender info
        messages = await MessageService.get_room_messages(
            session, updated_message.room_id, limit=1000, use_cache=False
        )
        
        # Find the updated message
        for msg in messages:
            if msg.message_id == message_id:
                return msg
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated message"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> None:
    """Delete a message (only sender can delete)."""
    try:
        success = await MessageService.delete_message(session, message_id, current_user.user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# Additional utility endpoints
@router.get("/rooms/{room_id}/search", response_model=List[MessageWithSenderInfo])
async def search_room_messages(
    room_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=20, le=50, ge=1, description="Number of results to return")
) -> List[MessageWithSenderInfo]:
    """Search messages in a room."""
    try:
        # Validate user is participant in the room
        is_participant = await MessageService.validate_message_access(
            session, room_id, current_user.user_id
        )
        
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a participant in the room to search messages"
            )
        
        # Search messages
        messages = await MessageService.search_messages(session, room_id, q, limit)
        return messages
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search messages"
        )


@router.get("/rooms/{room_id}/after/{message_id}", response_model=List[MessageWithSenderInfo])
async def get_messages_after(
    room_id: UUIDType,
    message_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100, ge=1, description="Number of messages to retrieve")
) -> List[MessageWithSenderInfo]:
    """Get messages after a specific message ID (for pagination)."""
    try:
        # Validate user is participant in the room
        is_participant = await MessageService.validate_message_access(
            session, room_id, current_user.user_id
        )
        
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a participant in the room to view messages"
            )
        
        # Get messages after specified message
        messages = await MessageService.get_messages_after(session, room_id, message_id, limit)
        return messages
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )


@router.get("/rate-limit", response_model=RateLimitInfo)
async def get_rate_limit_info(
    current_user: CurrentUser
) -> RateLimitInfo:
    """Get current rate limit information for the user."""
    rate_info = await MessageService.get_rate_limit_info(current_user.user_id)
    return RateLimitInfo(**rate_info)