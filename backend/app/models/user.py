from uuid import uuid4


from sqlalchemy import Column, Integer, String, DateTime, String
from pydantic import BaseModel, EmailStr
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(50))
    profile_picture_url = Column(String(255))
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    
