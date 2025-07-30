import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base


# pydantic model for API validation
class RoomParticipantCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID


class RoomParticipantGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime


# Sqlalchemy model for database
class RoomParticipant(Base):
    __tablename__ = "room_participants"

    room_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_rooms.room_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    joined_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
