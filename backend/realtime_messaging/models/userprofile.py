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

    phone_number: str | None = Field(
        default=None, examples=["012346789"], description="User's phone number"
    )
    address: str | None = Field(
        default=None, examples=["123 Main St"], description="User's address"
    )
    city: str | None = Field(
        default=None, max_length=100, examples=["New York"], description="User's city"
    )
    country: str | None = Field(
        default=None, max_length=100, examples=["USA"], description="User's country"
    )
    postal_code: str | None = Field(
        default=None,
        max_length=20,
        examples=["10001"],
        description="User's postal code",
    )
    date_of_birth: date | None = Field(
        default=None, examples=["1990-01-01"], description="User's date of birth"
    )
    gender: Gender | None = Field(default=None, description="User's gender")
    marital_status: MaritalStatus | None = Field(
        default=None, description="User's marital status"
    )
    company: str | None = Field(default=None, description="User's company")
    education: str | None = Field(
        default=None, max_length=255, description="User's education"
    )
    bio: str | None = Field(default=None, description="User's bio")

    @field_validator("phone_number")
    def validate_phone_number(cls, value):
        if value and (len(value) < 10 or len(value) > 15):
            raise ValueError("Phone number must be between 10 and 15 characters.")
        return value

    @field_validator("date_of_birth")
    def validate_date_of_birth(cls, value):
        if value and value >= date.today():
            raise ValueError("Date of birth cannot be today or in the future.")
        return value


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


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
