from typing import Annotated
import logging
import pytz
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession


from realtime_messaging.db.depends import get_db
from realtime_messaging.dependencies import security, CurrentUser
from realtime_messaging.models.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    LogoutResponse,
    UserTokenInfo,
)
from realtime_messaging.models.user import UserCreate
from realtime_messaging.services.auth import AuthService

from realtime_messaging.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PREFIX = "/auth"
tags = ["authentication"]

router = APIRouter(prefix=PREFIX, tags=tags)



@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    register_data: RegisterRequest, session: Annotated[AsyncSession, Depends(get_db)]
) -> RegisterResponse:
    """Register a new user."""
    try:
        # Create UserCreate object from RegisterRequest
        user_create = UserCreate(
            email=register_data.email,
            username=register_data.username,
            password=register_data.password,
            display_name=register_data.display_name,
            profile_picture_url=register_data.profile_picture_url,
        )

        # Register the user
        user = await AuthService.register_user(session, user_create)

        # Apply configured timezone to created_at
        tz = pytz.timezone(settings.SYSTEM_TIMEZONE)
        created_at_with_tz = user.created_at.astimezone(tz).isoformat()

        # Create user info for response
        user_info = UserTokenInfo(
            user_id=str(user.user_id),
            email=user.email,
            username=user.username,
            display_name=user.display_name,
            created_at=created_at_with_tz,
        )

        return RegisterResponse(message="User registered successfully", user=user_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"An error occured during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest, session: Annotated[AsyncSession, Depends(get_db)]
) -> LoginResponse:
    """Authenticate user and return JWT token."""
    try:
        # Authenticate user
        user = await AuthService.authenticate_user(
            session, login_data.email, login_data.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create tokens
        token_data = AuthService.create_tokens_for_user(user)

        return LoginResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            expires_in=token_data["expires_in"],
            user=UserTokenInfo(**token_data["user"]),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"An error occurred during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> LogoutResponse:
    """Logout user by blacklisting the JWT token."""
    try:
        token = credentials.credentials
        await AuthService.blacklist_token(token)

        return LogoutResponse(message="Successfully logged out")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.get("/me", response_model=UserTokenInfo)
async def get_current_user_info(current_user: CurrentUser) -> UserTokenInfo:
    """Get current authenticated user information."""
    return UserTokenInfo(
        user_id=str(current_user.user_id),
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        created_at=current_user.created_at.isoformat(),
    )


@router.post("/verify-token")
async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Verify if a JWT token is valid."""
    try:
        token = credentials.credentials
        user = await AuthService.get_user_by_token(session, token)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        return {
            "valid": True,
            "user_id": str(user.user_id),
            "email": user.email,
            "username": user.username,
        }

    except HTTPException:
        raise
    except Exception:
        return {"valid": False}
