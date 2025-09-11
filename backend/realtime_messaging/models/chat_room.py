import uuid
from datetime import datetime
from typing import Dict, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from .base import Base


DEFAULT_ROOM_SETTINGS = {
    "allow_editing": True,
    "theme": {
        "background": "#ffffff",
        "text_color": "#000000",
        "accent_color": "#007bff",
    },
    "file_sharing": True,
}


class PublicRoomSummary(BaseModel):
    """Summary info for public room browsing."""

    room_id: uuid.UUID
    name: str
    description: str | None
    participant_count: int
    max_participants: int | None
    avatar_url: str | None
    created_at: datetime
    creator_username: str


# Shared validation methods
class ChatRoomValidators:
    @staticmethod
    def validate_settings_structure(value):
        """Shared validation logic for settings field"""
        if value is not None:
            # Validate common settings structure
            allowed_keys = {
                "allow_editing",
                "theme",
                "file_sharing",
            }

            for key in value.keys():
                if key not in allowed_keys:
                    raise ValueError(f"Invalid settings key: {key}")

            # Validate theme structure if present
            if "theme" in value:
                theme = value["theme"]
                if not isinstance(theme, dict):
                    raise ValueError("Theme must be a dictionary")

                valid_theme_keys = {"background", "text_color", "accent_color"}
                for theme_key in theme.keys():
                    if theme_key not in valid_theme_keys:
                        raise ValueError(f"Invalid theme key: {theme_key}")

        return value

    @staticmethod
    def validate_description(value):
        if value is not None:
            value = value.strip()
            if len(value) == 0:
                return None
        return value


# Pydantic base model with shared fields and validation
class ChatRoomBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    name: str = Field(
        max_length=100, description="Name of the chat room", examples=["General Chat"]
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Brief description of the chat room's purpose",
        examples=["Team Project Discussion"],
    )
    is_private: bool = Field(
        default=False, description="Controls room access level (public vs private)"
    )
    max_participants: int | None = Field(
        default=None, ge=2, le=10, description="Maximum number of participants allowed"
    )
    avatar_url: str | None = Field(
        default=None,
        max_length=500,
        description="URL for the room's avatar or custom icon",
    )
    settings: Dict[str, Any] | None = Field(
        default=DEFAULT_ROOM_SETTINGS,
        description="Flexible configuration settings for the room",
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        return ChatRoomValidators.validate_description(value)

    # @field_validator("avatar_url")
    # @classmethod
    # def validate_avatar_url(cls, value):
    #     if value is not None:
    #         value = value.strip()
    #         if len(value) == 0:
    #             return None
    #         # Basic URL validation
    #         if not (value.startswith("http://") or value.startswith("https://")):
    #             raise ValueError("Avatar URL must be a valid HTTP/HTTPS URL")
    #     return value

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, value):
        return ChatRoomValidators.validate_settings_structure(value)


# Pydantic model for API validation
class ChatRoomCreate(ChatRoomBase):
    pass


# Base class for update operations with optional fields
class ChatRoomUpdateBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = Field(
        default=None, max_length=100, description="New name for the chat room"
    )
    description: str | None = Field(
        default=None, max_length=500, description="New description for the chat room"
    )
    is_private: bool | None = Field(
        default=None, description="Update room access level"
    )
    max_participants: int | None = Field(
        default=None, ge=2, le=10, description="Update maximum participants limit"
    )
    avatar_url: str | None = Field(
        default=None, max_length=500, description="Update room avatar URL"
    )
    settings: Dict[str, Any] | None = Field(
        default=None, description="Update room settings"
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        return ChatRoomValidators.validate_description(value)

    # @field_validator("avatar_url")
    # @classmethod
    # def validate_avatar_url(cls, value):
    #     if value is not None:
    #         value = value.strip()
    #         if len(value) == 0:
    #             return None
    #         if not (value.startswith("http://") or value.startswith("https://")):
    #             raise ValueError("Avatar URL must be a valid HTTP/HTTPS URL")
    #     return value

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, value):
        return ChatRoomValidators.validate_settings_structure(value)


class ChatRoomUpdate(ChatRoomUpdateBase):
    pass


class ChatRoomGet(ChatRoomBase):
    room_id: uuid.UUID
    creator_id: uuid.UUID
    created_at: datetime
    updated_at: datetime | None = None


# SQLAlchemy model for database
class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    room_id: uuid.UUID = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    name: str = Column(String(100), nullable=False)
    description: str | None = Column(String(500), nullable=True)
    creator_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_private: bool = Column(Boolean, nullable=False, default=False)
    max_participants: int | None = Column(Integer, nullable=True)
    avatar_url: str | None = Column(String(500), nullable=True)
    settings: Dict[str, Any] | None = Column(JSONB, nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: datetime | None = Column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )
