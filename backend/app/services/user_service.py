from typing import Optional
from uuid import UUID as UUIDType

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from backend.app.models.user import User, UserCreate, UserGet, UserUpdate


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service class for user operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def create_user(session: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user in the database."""
        try:
            # Hash the password
            hashed_password = UserService.hash_password(user_data.password)
            
            # Create user instance
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                display_name=user_data.display_name,
                profile_picture_url=user_data.profile_picture_url,
            )
            
            # Add to session and commit
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
            
            return db_user
            
        except IntegrityError as e:
            await session.rollback()
            if "email" in str(e):
                raise ValueError("Email already exists")
            elif "username" in str(e):
                raise ValueError("Username already exists")
            else:
                raise ValueError("User creation failed due to constraint violation")

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: UUIDType) -> Optional[User]:
        """Get a user by their ID."""
        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
        """Get a user by their email."""
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
        """Get a user by their username."""
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user(
        session: AsyncSession, user_id: UUIDType, user_data: UserUpdate
    ) -> Optional[User]:
        """Update a user's information."""
        # Get the existing user
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            return None

        # Update only provided fields
        if user_data.username is not None:
            user.username = user_data.username
        if user_data.display_name is not None:
            user.display_name = user_data.display_name
        if user_data.profile_picture_url is not None:
            user.profile_picture_url = user_data.profile_picture_url

        try:
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError:
            await session.rollback()
            raise ValueError("Username already exists")

    @staticmethod
    async def delete_user(session: AsyncSession, user_id: UUIDType) -> bool:
        """Delete a user by their ID."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            return False

        await session.delete(user)
        await session.commit()
        return True

    @staticmethod
    async def authenticate_user(
        session: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = await UserService.get_user_by_email(session, email)
        if not user:
            return None
        
        if not UserService.verify_password(password, user.hashed_password):
            return None
            
        return user

    @staticmethod
    async def update_user_profile(
        session: AsyncSession, user_id: UUIDType, profile_data: UserUpdate
    ) -> Optional[User]:
        """Update user profile with validation for profile-specific fields."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            return None

        # Validate display_name length if provided
        if profile_data.display_name is not None:
            if len(profile_data.display_name.strip()) == 0:
                raise ValueError("Display name cannot be empty")
            if len(profile_data.display_name) > 50:
                raise ValueError("Display name must be 50 characters or less")

        # Validate profile picture URL if provided
        if profile_data.profile_picture_url is not None:
            if profile_data.profile_picture_url and len(profile_data.profile_picture_url) > 255:
                raise ValueError("Profile picture URL must be 255 characters or less")

        # Validate username if provided
        if profile_data.username is not None:
            if len(profile_data.username.strip()) == 0:
                raise ValueError("Username cannot be empty")
            if len(profile_data.username) > 50:
                raise ValueError("Username must be 50 characters or less")
            
            # Check if username is already taken by another user
            existing_user = await UserService.get_user_by_username(session, profile_data.username)
            if existing_user and existing_user.user_id != user_id:
                raise ValueError("Username already exists")

        # Update only provided fields
        if profile_data.username is not None:
            user.username = profile_data.username.strip()
        if profile_data.display_name is not None:
            user.display_name = profile_data.display_name.strip() if profile_data.display_name else None
        if profile_data.profile_picture_url is not None:
            user.profile_picture_url = profile_data.profile_picture_url

        try:
            await session.commit()
            await session.refresh(user)
            return user
        except IntegrityError:
            await session.rollback()
            raise ValueError("Username already exists")

    @staticmethod
    async def get_user_profile_summary(session: AsyncSession, user_id: UUIDType) -> Optional[dict]:
        """Get a summary of user profile information."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            return None
            
        return {
            "user_id": str(user.user_id),
            "username": user.username,
            "display_name": user.display_name,
            "profile_picture_url": user.profile_picture_url,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
