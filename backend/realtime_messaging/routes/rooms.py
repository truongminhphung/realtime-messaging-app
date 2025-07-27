from typing import List
from uuid import UUID as UUIDType

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from realtime_messaging.db.depends import get_db
from realtime_messaging.models.chat_room import ChatRoomCreate, ChatRoomGet, ChatRoomUpdate
from realtime_messaging.models.room_participant import RoomParticipantGet
from realtime_messaging.services.room_service import RoomService
from realtime_messaging.dependencies import CurrentUser


router = APIRouter(prefix="/rooms", tags=["rooms"])


# Pydantic models for request/response
class RoomInviteRequest(BaseModel):
    email: EmailStr


class RoomJoinResponse(BaseModel):
    message: str
    room_id: UUIDType


class RoomLeaveResponse(BaseModel):
    message: str


class RoomParticipant(BaseModel):
    user_id: UUIDType
    username: str
    display_name: str | None
    profile_picture_url: str | None
    joined_at: str


class RoomWithDetails(BaseModel):
    room_id: UUIDType
    name: str
    creator_id: UUIDType
    created_at: str
    participant_count: int


# Room CRUD endpoints
@router.post("/", response_model=ChatRoomGet, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: ChatRoomCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ChatRoomGet:
    """Create a new chat room."""
    try:
        if not room_data.name or len(room_data.name.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room name cannot be empty",
            )

        if len(room_data.name.strip()) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room name must be 100 characters or less",
            )

        room = await RoomService.create_room(session, room_data, current_user.user_id)
        return ChatRoomGet.model_validate(room)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[ChatRoomGet])
async def get_user_rooms(
    current_user: CurrentUser, session: AsyncSession = Depends(get_db)
) -> List[ChatRoomGet]:
    """Get all rooms that the current user is a participant in."""
    try:
        rooms = await RoomService.get_user_rooms(session, current_user.user_id)
        return [ChatRoomGet.model_validate(room) for room in rooms]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rooms",
        )


@router.get("/{room_id}", response_model=RoomWithDetails)
async def get_room_details(
    room_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> RoomWithDetails:
    """Get detailed information about a specific room."""
    try:
        # Check if user is a participant
        is_participant = await RoomService.is_user_participant(
            session, room_id, current_user.user_id
        )

        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a participant to view room details",
            )

        room_details = await RoomService.get_room_with_participant_count(
            session, room_id
        )
        if not room_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
            )

        return RoomWithDetails(**room_details)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve room details",
        )


@router.put("/{room_id}", response_model=ChatRoomGet)
async def update_room(
    room_id: UUIDType,
    room_data: ChatRoomUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ChatRoomGet:
    """Update room details (only room creator can update)."""
    try:
        if room_data.name is not None:
            if len(room_data.name.strip()) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Room name cannot be empty",
                )

            if len(room_data.name.strip()) > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Room name must be 100 characters or less",
                )

        updated_room = await RoomService.update_room(
            session,
            room_id,
            current_user.user_id,
            room_data.model_dump(exclude_unset=True),
        )

        if not updated_room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
            )

        return ChatRoomGet.model_validate(updated_room)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a room (only room creator can delete)."""
    try:
        success = await RoomService.delete_room(session, room_id, current_user.user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Room not found"
            )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# Room participation endpoints
@router.post("/{room_id}/invite", status_code=status.HTTP_200_OK)
async def invite_user_to_room(
    room_id: UUIDType,
    invite_data: RoomInviteRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Send an invitation to a user to join the room."""
    try:
        success = await RoomService.invite_user_to_room(
            session, room_id, current_user.user_id, invite_data.email
        )

        if success:
            return {
                "message": f"Invitation sent to {invite_data.email}",
                "room_id": room_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send invitation",
            )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{room_id}/join", response_model=RoomJoinResponse)
async def join_room(
    room_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> RoomJoinResponse:
    """Join a room as a participant."""
    try:
        success = await RoomService.join_room(session, room_id, current_user.user_id)

        if success:
            return RoomJoinResponse(
                message="Successfully joined the room", room_id=room_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to join room",
            )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{room_id}/leave", response_model=RoomLeaveResponse)
async def leave_room(
    room_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> RoomLeaveResponse:
    """Leave a room (remove current user from participants)."""
    try:
        success = await RoomService.leave_room(session, room_id, current_user.user_id)

        if success:
            return RoomLeaveResponse(message="Successfully left the room")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are not a participant in this room",
            )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{room_id}/participants", response_model=List[RoomParticipant])
async def get_room_participants(
    room_id: UUIDType,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> List[RoomParticipant]:
    """Get all participants in a room."""
    try:
        # Check if user is a participant
        is_participant = await RoomService.is_user_participant(
            session, room_id, current_user.user_id
        )

        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a participant to view room participants",
            )

        participants_data = await RoomService.get_room_participants(session, room_id)

        participants = []
        for participant in participants_data:
            participants.append(
                RoomParticipant(
                    user_id=UUIDType(participant["user_id"]),
                    username=participant["username"],
                    display_name=participant["display_name"],
                    profile_picture_url=participant["profile_picture_url"],
                    joined_at=participant["joined_at"],
                )
            )

        return participants

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve room participants",
        )
