from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from uuid import UUID as UUIDType

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from realtime_messaging.config import settings
from realtime_messaging.models.user import User, UserCreate
from realtime_messaging.services.user_service import UserService

from realtime_messaging.exceptions import DBItemExistsError

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for token blacklisting
print(f"Connecting to Redis at {settings.redis_url}")
redis_client = redis.from_url(settings.redis_url)


class AuthService:
    """Service for authentication operations including JWT and password management."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.jwt_access_token_expire_minutes
            )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    @staticmethod
    async def verify_token(token: str) -> Optional[dict]:
        """Verify a JWT token and return the payload."""
        # make sure the token starts with 'Bearer '
        if not token.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization Header",
            )
        token = token.split(" ", 1)[1]
        try:
            # Check if token is blacklisted (with fallback if Redis unavailable)
            try:
                is_blacklisted = await redis_client.get(f"blacklist:{token}")
                if is_blacklisted:
                    return None
            except Exception as redis_error:
                # If Redis is unavailable, log the error but continue with token verification
                print(f"Warning: Redis unavailable for blacklist check: {redis_error}")
                # Continue without blacklist check

            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is invalid or expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    async def blacklist_token(token: str) -> None:
        """Add a token to the blacklist in Redis."""
        try:
            # Decode token to get expiration time
            processed_token = (
                token.split(" ", 1)[1] if token.lower().startswith("bearer ") else token
            )
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            exp = payload.get("exp")
            if exp:
                # Calculate TTL (time to live) until token expires
                current_time = datetime.now(timezone.utc).timestamp()
                ttl = max(0, int(exp - current_time))

                # Store in Redis with TTL
                await redis_client.setex(f"blacklist:{processed_token}", ttl, "1")
        except JWTError:
            # If token is invalid, still try to blacklist it for a short time
            await redis_client.setex(
                f"blacklist:{processed_token}", settings.TTL, "1"
            )  # 1 hour

    @staticmethod
    async def register_user(session: AsyncSession, user_data: UserCreate) -> User:
        """Register a new user with hashed password."""
        try:
            # Check if user already exists
            existing_user_email = await UserService.get_user_by_email(
                session, user_data.email
            )
            if existing_user_email:
                raise DBItemExistsError(
                    f"User with email {user_data.email} already exists"
                )
            existing_user_username = await UserService.get_user_by_username(
                session, user_data.username
            )
            if existing_user_username:
                raise DBItemExistsError(
                    f"User with username {user_data.username} already exists"
                )
            # Create user using UserService
            user = await UserService.create_user(session, user_data)
            return user

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @staticmethod
    async def authenticate_user(
        session: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = await UserService.get_user_by_email(session, email)
        if not user:
            return None

        if not AuthService.verify_password(password, user.hashed_password):
            return None

        return user

    @staticmethod
    async def get_user_by_token(session: AsyncSession, token: str) -> Optional[User]:
        """Get user from JWT token."""
        payload = await AuthService.verify_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        try:
            user_uuid = UUIDType(user_id)
            user = await UserService.get_user_by_id(session, user_uuid)
            return user
        except (ValueError, TypeError):
            return None

    @staticmethod
    def create_tokens_for_user(user: User) -> dict:
        """Create access tokens for a user."""
        access_token_expires = timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        access_token = AuthService.create_access_token(
            data={
                "sub": str(user.user_id),
                "email": user.email,
                "username": user.username,
            },
            expires_delta=access_token_expires,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,  # in seconds
            "user": {
                "user_id": str(user.user_id),
                "email": user.email,
                "username": user.username,
                "display_name": user.display_name,
                "created_at": user.created_at.isoformat(),
            },
        }
