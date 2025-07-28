import re
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from uuid import UUID as UUIDType
from datetime import datetime


from fastapi import APIRouter, HTTPException, status


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
    
    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        """Validate email format for login."""
        if not v:
            raise ValueError("Email is required")
        
        email_str = str(v).strip()
        
        if not email_str:
            raise ValueError("Email cannot be empty")
        
        # Basic email format check
        if "@" not in email_str or "." not in email_str.split("@")[-1]:
            raise ValueError("Invalid email format")
        
        try:
            from pydantic import EmailStr
            return EmailStr._validate(email_str, None, None)
        except Exception:
            raise ValueError("Invalid email format")
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password is provided."""
        if not v:
            raise ValueError("Password is required")
        
        return str(v)


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str
    expires_in: int
    user: UserTokenInfo


class RegisterRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    """Registration request model."""
    email: EmailStr
    username: str
    password: str
    display_name: str | None = None
    profile_picture_url: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        """Validate email format and provide clear error messages."""
        if not v:
            raise ValueError("Email is required")
        
        # Convert to string if needed
        email_str = str(v).strip()
        
        if not email_str:
            raise ValueError("Email cannot be empty")
        
        # Basic email format check before Pydantic validation
        if "@" not in email_str or "." not in email_str.split("@")[-1]:
            raise ValueError("Invalid email format")
        
        try:
            # Let EmailStr do the proper validation
            from pydantic import EmailStr
            return EmailStr._validate(email_str)
        except Exception as e:
            print(f"Email validation error: {e}")  # Debugging line
            raise ValueError("Invalid email format")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not v:
            raise ValueError("Username is required")
        
        username = str(v).strip()
        
        if not username:
            raise ValueError("Username cannot be empty")
        
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        
        if len(username) > 20:
            raise ValueError("Username must be at most 20 characters long")
        
        # Allow alphanumeric, underscore, and hyphen
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        
        return username
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if not v:
            raise ValueError("Password is required")
        
        password = str(v)
        
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if len(password) > 128:
            raise ValueError("Password must be at most 128 characters long")
        
        # Check for at least one uppercase, one lowercase, one digit
        if not re.search(r'[A-Z]', password):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            raise ValueError("Password must contain at least one digit")
        
        return password

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
