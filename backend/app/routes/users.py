from typing import List
from uuid import UUID as UUIDType

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.depends import get_db
from backend.app.models.user import UserCreate, UserGet, UserUpdate
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserGet, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db)
) -> UserGet:
    """Create a new user."""
    try:
        user = await UserService.create_user(session, user_data)
        return UserGet.model_validate(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{user_id}", response_model=UserGet)
async def get_user(
    user_id: UUIDType,
    session: AsyncSession = Depends(get_db)
) -> UserGet:
    """Get a user by ID."""
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
    """Get a user by email."""
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
    """Get a user by username."""
    user = await UserService.get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserGet.model_validate(user)


@router.put("/{user_id}", response_model=UserGet)
async def update_user(
    user_id: UUIDType,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_db)
) -> UserGet:
    """Update a user's information."""
    try:
        user = await UserService.update_user(session, user_id, user_data)
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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUIDType,
    session: AsyncSession = Depends(get_db)
) -> None:
    """Delete a user."""
    success = await UserService.delete_user(session, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )