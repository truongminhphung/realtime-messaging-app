import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base


# Pydantic model for API validation
class ChatRoomCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class ChatRoomUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None


class ChatRoomGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: uuid.UUID
    name: str
    creator_id: uuid.UUID
    created_at: datetime


# sqlalchemy model for database
class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    room_id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    name = Column(String(100), nullable=False)
    creator_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
