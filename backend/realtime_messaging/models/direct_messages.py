from uuid import UUID
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class DirectMessageRoomInfo(BaseModel):
    room_id: UUID
    other_user_id: UUID
    other_username: str
    other_display_name: str | None
    other_profile_picture_url: str | None
    is_online: bool = False
    last_message: str | None = None
    last_message_at: datetime | None = None
    unread_count: int = 0


class DirectMessageInitiate(BaseModel):
    """Request to start a direct message conversation."""

    other_user_id: UUID
