from pydantic import BaseModel, EmailStr
from uuid import UUID as UUIDType
from datetime import datetime


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    expires_in: int
    user: "UserTokenInfo"


class UserTokenInfo(BaseModel):
    """User info included in token response."""
    user_id: str
    email: EmailStr
    username: str
    display_name: str | None = None
    created_at: str


class TokenData(BaseModel):
    """Token data for internal use."""
    user_id: UUIDType | None = None
    email: str | None = None
    username: str | None = None


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str
    expires_in: int
    user: UserTokenInfo


class RegisterRequest(BaseModel):
    """Registration request model."""
    email: EmailStr
    username: str
    password: str
    display_name: str | None = None
    profile_picture_url: str | None = None


class RegisterResponse(BaseModel):
    """Registration response model."""
    message: str
    user: UserTokenInfo


class LogoutResponse(BaseModel):
    """Logout response model."""
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
