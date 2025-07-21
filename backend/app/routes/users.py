from typing import List
from uuid import UUID as UUIDType

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.depends import get_db
from app.models.user import UserCreate, UserGet, UserUpdate
from app.services.user_service import UserService
from app.dependencies import CurrentUser


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserGet)
async def get_current_user_profile(
    current_user: CurrentUser
) -> UserGet:
    """Get current authenticated user profile."""
    return UserGet.model_validate(current_user)


@router.put("/me", response_model=UserGet)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
) -> UserGet:
    """Update current authenticated user profile."""
    try:
        user = await UserService.update_user(session, current_user.user_id, user_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserGet.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Public endpoints for getting user information
@router.get("/{user_id}", response_model=UserGet)
async def get_user_by_id(
    user_id: UUIDType,
    session: AsyncSession = Depends(get_db)
) -> UserGet:
    """Get a user by ID (public endpoint)."""
    user = await UserService.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserGet.model_validate(user)


@router.get("/email/{email}", response_model=UserGet)
async def get_user_by_email(
    email: str,
    session: AsyncSession = Depends(get_db)
) -> UserGet:
    """Get a user by email (public endpoint)."""
    user = await UserService.get_user_by_email(session, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserGet.model_validate(user)


@router.get("/username/{username}", response_model=UserGet)
async def get_user_by_username(
    username: str,
    session: AsyncSession = Depends(get_db)
) -> UserGet:
    """Get a user by username (public endpoint)."""
    user = await UserService.get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserGet.model_validate(user)