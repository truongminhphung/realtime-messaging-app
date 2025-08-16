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
    TokenVerificationResponse,
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

        logger.info(f"User registered: {user.username} ({user.email})")
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
        try:
            user = await AuthService.authenticate_user(
                session, login_data.email, login_data.password
            )
        except HTTPException as e:
            print("HTTPException occurred: ", e)
            raise
        print("print user: ", user)

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
    # current_user: CurrentUser
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


@router.post("/verify-token", response_model=TokenVerificationResponse)
async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenVerificationResponse:
    """
    Verify if a JWT token is valid and return user information.

    Returns token validity status along with user information if valid.
    This endpoint follows industry standards for token verification.
    """
    try:
        token = credentials.credentials

        # First verify the token structure and signature
        payload = await AuthService.verify_token(f"Bearer {token}")
        if not payload:
            return TokenVerificationResponse(valid=False)

        # Get user information from database using the raw token
        user = await AuthService.get_user_by_token(session, f"Bearer {token}")
        if not user:
            return TokenVerificationResponse(valid=False)

        # Extract expiration time from payload
        expires_at = payload.get("exp")

        return TokenVerificationResponse(
            valid=True,
            user_id=str(user.user_id),
            email=user.email,
            username=user.username,
            display_name=user.display_name,
            expires_at=expires_at,
        )

    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            return TokenVerificationResponse(valid=False)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        return TokenVerificationResponse(valid=False)
