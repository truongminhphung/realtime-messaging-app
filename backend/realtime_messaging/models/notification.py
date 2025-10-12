import uuid
import enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, String, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime

from .base import Base


class NotificationType(enum.Enum):
    ROOM_INVITATION = "room_invitation"
    NEW_MESSAGE = "new_message"
    FRIEND_REQUEST = "friend_request"
    FRIEND_REQUEST_ACCEPTED = "friend_request_accepted"

    def __str__(self):
        return self.value


class NotificationStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# Pydantic model for API validation
class NotificationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    type: NotificationType
    content: str


class NotificationGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    content: str
    status: NotificationStatus
    is_read: bool
    created_at: datetime
    updated_at: datetime | None = None


class NotificationUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_read: bool | None = None
    status: NotificationStatus | None = None


# sqlalchemy model for database
class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(Enum(NotificationType), nullable=False)
    content = Column(String(500), nullable=False)  # Increased length for more content
    status = Column(
        Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING
    )
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
