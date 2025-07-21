import uuid
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime

from .base import Base


# Pydantic model for API validation
class MessageCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    room_id: uuid.UUID
    sender_id: uuid.UUID
    content: str

class MessageGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    room_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    created_at: datetime

class MessageUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content: str | None = None



# sqlalchemy model for database
class Message(Base):
    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chat_rooms.room_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(String(500), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )