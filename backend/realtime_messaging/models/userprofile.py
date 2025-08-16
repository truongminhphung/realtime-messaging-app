import uuid
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import Column, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship

from .base import Base


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

    def __str__(self):
        return self.value


class MaritalStatus(str, Enum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

    def __str__(self):
        return self.value


# Pydantic models for API validation
# It follows Inheritance concept of OOP
class UserProfileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phone_number: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    postal_code: str | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    marital_status: MaritalStatus | None = None
    company: str | None = None
    education: str | None = None
    bio: str | None = None

    @field_validator("phone_number")
    def validate_phone_number(cls, value):
        if len(value) < 10 or len(value) > 15:
            raise ValueError("Phone number must be between 10 and 15 characters.")

    @field_validator("date_of_birth")
    def validate_date_of_birth(cls, value):
        if value >= date.today():
            raise ValueError("Date of birth cannot be today or in the future.")
        return value


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileGet(UserProfileBase):
    user_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


# SQLAlchemy model
class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    user = relationship("User", back_populates="profile")
    phone_number = Column(String(20))
    address = Column(String(255))
    city = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    date_of_birth = Column(Date)
    gender = Column(SQLAlchemyEnum(Gender))
    marital_status = Column(SQLAlchemyEnum(MaritalStatus))
    company = Column(String(100))
    education = Column(String(255))
    bio = Column(Text)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
