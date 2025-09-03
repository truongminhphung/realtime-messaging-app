from uuid import uuid4, UUID as UUIDType
from datetime import datetime

from sqlalchemy import Column, String, DateTime
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


# Pydantic model for API validation
class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # use plain str here so our validator can intercept first
    email: EmailStr
    username: str
    password: str
    display_name: str | None = None
    profile_picture_url: str | None = None


class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str | None = None
    display_name: str | None = None
    profile_picture_url: str | None = None


class UserGet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUIDType
    email: EmailStr
    username: str
    display_name: str | None = None
    profile_picture_url: str | None = None
    created_at: datetime
    updated_at: datetime


# sqlalchemy model for database
class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(50))
    profile_picture_url = Column(String(255))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now()
    )
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
