import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base


# Pydantic model for API validation
class ChatRoomCreate(BaseModel):
    name: str

    class Config:
        orm_mode = True
        from_attributes = True
        allow_population_by_field_name = True


class ChatRoomUpdate(BaseModel):
    name: str | None = None

    class Config:
        orm_mode = True
        from_attributes = True
        allow_population_by_field_name = True


class ChatRoomGet(BaseModel):
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
