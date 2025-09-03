from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from realtime_messaging.models.userprofile import (
    UserProfile,
    UserProfileGet,
    UserProfileUpdate,
)


class UserProfileService:
    """Service for managing user profiles."""

    @staticmethod
    async def get_user_profile(session: AsyncSession, user_id: UUID):
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def update_user_profile(
        session: AsyncSession, user_id: UUID, profile_data: UserProfileUpdate
    ) -> None:
        """Update user profile with partial data."""
        if not profile_data:
            return

        profile = await UserProfileService.get_user_profile(session, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found"
            )

        try:
            for key, value in profile_data.model_dump(exclude_unset=True).items():
                setattr(profile, key, value)

            session.add(profile)
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile",
            )
        await session.refresh(profile)
