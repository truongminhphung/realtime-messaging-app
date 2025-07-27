from typing import List, Optional
from uuid import UUID as UUIDType

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from realtime_messaging.db.depends import get_db
from realtime_messaging.dependencies import get_current_user
from realtime_messaging.models.user import User
from realtime_messaging.models.notification import (
    NotificationGet, 
    NotificationUpdate, 
    NotificationType, 
    NotificationStatus
)
from realtime_messaging.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=List[NotificationGet])
async def get_user_notifications(
    skip: int = Query(0, ge=0, description="Number of notifications to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications to return"),
    notification_type: Optional[NotificationType] = Query(None, description="Filter by notification type"),
    status: Optional[NotificationStatus] = Query(None, description="Filter by notification status"),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get notifications for the authenticated user.
    
    - **skip**: Number of notifications to skip for pagination
    - **limit**: Maximum number of notifications to return (1-100)
    - **notification_type**: Filter by specific notification type
    - **status**: Filter by notification status 
    - **unread_only**: If true, return only unread notifications
    """
    try:
        notifications = await NotificationService.get_user_notifications(
            session=session,
            user_id=current_user.user_id,
            skip=skip,
            limit=limit,
            notification_type=notification_type,
            status=status,
            unread_only=unread_only
        )
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve notifications: {str(e)}"
        )


@router.get("/count")
async def get_notification_count(
    unread_only: bool = Query(False, description="Count only unread notifications"),
    notification_type: Optional[NotificationType] = Query(None, description="Filter by notification type"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the total count of notifications for the authenticated user.
    
    - **unread_only**: If true, count only unread notifications
    - **notification_type**: Filter by specific notification type
    """
    try:
        count = await NotificationService.get_notification_count(
            session=session,
            user_id=current_user.user_id,
            notification_type=notification_type,
            unread_only=unread_only
        )
        
        return {
            "count": count,
            "unread_only": unread_only,
            "notification_type": notification_type
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification count: {str(e)}"
        )


@router.put("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: UUIDType,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a specific notification as read.
    
    - **notification_id**: The UUID of the notification to mark as read
    """
    try:
        success = await NotificationService.mark_as_read(
            session=session,
            notification_id=notification_id,
            user_id=current_user.user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or you don't have permission to modify it"
            )
        
        return {"message": "Notification marked as read successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.put("/read-all")
async def mark_all_notifications_as_read(
    notification_type: Optional[NotificationType] = Query(None, description="Mark all notifications of this type as read"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark all notifications as read for the authenticated user.
    
    - **notification_type**: If specified, only mark notifications of this type as read
    """
    try:
        count = await NotificationService.mark_all_as_read(
            session=session,
            user_id=current_user.user_id,
            notification_type=notification_type
        )
        
        return {
            "message": f"Successfully marked {count} notifications as read",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notifications as read: {str(e)}"
        )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: UUIDType,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific notification.
    
    - **notification_id**: The UUID of the notification to delete
    """
    try:
        success = await NotificationService.delete_notification(
            session=session,
            notification_id=notification_id,
            user_id=current_user.user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or you don't have permission to delete it"
            )
        
        return {"message": "Notification deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )


@router.delete("/")
async def delete_all_notifications(
    notification_type: Optional[NotificationType] = Query(None, description="Delete all notifications of this type"),
    read_only: bool = Query(False, description="Delete only read notifications"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete all notifications for the authenticated user.
    
    - **notification_type**: If specified, only delete notifications of this type
    - **read_only**: If true, only delete read notifications
    """
    try:
        count = await NotificationService.delete_user_notifications(
            session=session,
            user_id=current_user.user_id,
            notification_type=notification_type,
            read_only=read_only
        )
        
        return {
            "message": f"Successfully deleted {count} notifications",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notifications: {str(e)}"
        )


@router.get("/preferences")
async def get_notification_preferences(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get notification preferences for the authenticated user.
    """
    try:
        preferences = await NotificationService.get_user_preferences(
            session=session,
            user_id=current_user.user_id
        )
        
        return preferences
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification preferences: {str(e)}"
        )


@router.put("/preferences")
async def update_notification_preferences(
    email_notifications: Optional[bool] = None,
    push_notifications: Optional[bool] = None,
    new_message_notifications: Optional[bool] = None,
    room_invite_notifications: Optional[bool] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update notification preferences for the authenticated user.
    
    - **email_notifications**: Enable/disable email notifications
    - **push_notifications**: Enable/disable push notifications
    - **new_message_notifications**: Enable/disable new message notifications
    - **room_invite_notifications**: Enable/disable room invite notifications
    """
    try:
        preferences_data = {}
        if email_notifications is not None:
            preferences_data["email_notifications"] = email_notifications
        if push_notifications is not None:
            preferences_data["push_notifications"] = push_notifications
        if new_message_notifications is not None:
            preferences_data["new_message_notifications"] = new_message_notifications
        if room_invite_notifications is not None:
            preferences_data["room_invite_notifications"] = room_invite_notifications
        
        if not preferences_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one preference must be provided"
            )
        
        updated_preferences = await NotificationService.update_user_preferences(
            session=session,
            user_id=current_user.user_id,
            preferences=preferences_data
        )
        
        return {
            "message": "Notification preferences updated successfully",
            "preferences": updated_preferences
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification preferences: {str(e)}"
        )