from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from realtime_messaging.models.userprofile import UserProfileGet, UserProfileUpdate
from realtime_messaging.dependencies import CurrentUser
from realtime_messaging.db.depends import get_db
from realtime_messaging.services.userprofile_service import UserProfileService

router = APIRouter(prefix="/userprofiles", tags=["userprofiles"])


@router.get("/me", response_model=UserProfileGet)
async def get_current_user_profile(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileGet:
    """Get current user's profile information."""
    profile = await UserProfileService.get_user_profile(session, current_user.user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found"
        )
    return UserProfileGet.model_validate(profile)
