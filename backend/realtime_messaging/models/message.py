import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator
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
    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Message content (1-500 characters)",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate and clean message content."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")

        cleaned_content = v.strip()
        if len(cleaned_content) == 0:
            raise ValueError("Message content cannot be empty")

        if len(cleaned_content) > 500:
            raise ValueError("Message content must be 500 characters or less")

        return cleaned_content


class MessageGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    room_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    created_at: datetime


class MessageUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content: str | None = Field(
        None,
        min_length=1,
        max_length=500,
        description="Updated message content (1-500 characters)",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        """Validate and clean message content."""
        if v is None:
            return v

        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")

        cleaned_content = v.strip()
        if len(cleaned_content) == 0:
            raise ValueError("Message content cannot be empty")

        if len(cleaned_content) > 500:
            raise ValueError("Message content must be 500 characters or less")

        return cleaned_content


class MessageCreateInternal(BaseModel):
    """Internal model for creating messages (used by services)."""

    model_config = ConfigDict(from_attributes=True)

    room_id: uuid.UUID
    sender_id: uuid.UUID
    content: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Message content (1-500 characters)",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate and clean message content."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")

        cleaned_content = v.strip()
        if len(cleaned_content) == 0:
            raise ValueError("Message content cannot be empty")

        if len(cleaned_content) > 500:
            raise ValueError("Message content must be 500 characters or less")

        return cleaned_content


class SenderInfo(BaseModel):
    """Sender information for message display."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    username: str
    display_name: str | None = None


class MessageWithSenderInfo(BaseModel):
    """Message with detailed sender information for API responses."""

    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    room_id: uuid.UUID
    sender_id: uuid.UUID
    sender_username: str
    sender_display_name: str | None = None
    sender_profile_picture_url: str | None = None
    content: str
    created_at: datetime

    @property
    def sender(self) -> SenderInfo:
        """Get sender info in the expected format for WebSocket."""
        return SenderInfo(
            user_id=self.sender_id,
            username=self.sender_username,
            display_name=self.sender_display_name,
        )


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
