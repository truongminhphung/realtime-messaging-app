from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
import json
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, update, delete
from sqlalchemy.exc import IntegrityError
import redis.asyncio as redis

from realtime_messaging.models.notification import (
    Notification, 
    NotificationGet, 
    NotificationType, 
    NotificationStatus
)
from realtime_messaging.models.user import User
from realtime_messaging.config import settings


# Configure logging
logger = logging.getLogger(__name__)

# Redis client for caching
redis_client = redis.from_url(settings.redis_url)

# Cache settings
NOTIFICATION_CACHE_TTL = 300  # 5 minutes
NOTIFICATION_COUNT_CACHE_TTL = 60  # 1 minute


class NotificationService:
    """Service class for notification operations."""

    @staticmethod
    async def get_user_notifications(
        session: AsyncSession,
        user_id: UUIDType,
        skip: int = 0,
        limit: int = 50,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        unread_only: bool = False
    ) -> List[NotificationGet]:
        """Get notifications for a user with filtering and pagination."""
        try:
            # Build cache key
            cache_key = f"user_notifications:{user_id}:{skip}:{limit}:{notification_type}:{status}:{unread_only}"
            
            # Try cache first
            cached = await redis_client.get(cache_key)
            if cached:
                try:
                    cached_data = json.loads(cached)
                    return [NotificationGet(**notif) for notif in cached_data]
                except (json.JSONDecodeError, ValueError):
                    pass
            
            # Build query
            stmt = select(Notification).where(Notification.user_id == user_id)
            
            # Apply filters
            if notification_type:
                stmt = stmt.where(Notification.type == notification_type)
            
            if status:
                stmt = stmt.where(Notification.status == status)
            
            if unread_only:
                stmt = stmt.where(Notification.is_read == False)
            
            # Apply ordering and pagination
            stmt = stmt.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
            
            result = await session.execute(stmt)
            notifications = result.scalars().all()
            
            # Convert to response model
            notification_list = []
            for notification in notifications:
                notification_data = NotificationGet(
                    notification_id=notification.notification_id,
                    user_id=notification.user_id,
                    type=notification.type,
                    content=notification.content,
                    status=notification.status,
                    is_read=notification.is_read,
                    created_at=notification.created_at,
                    updated_at=notification.updated_at
                )
                notification_list.append(notification_data)
            
            # Cache the result
            if notification_list:
                cache_data = [notif.model_dump(mode='json') for notif in notification_list]
                await redis_client.setex(
                    cache_key,
                    NOTIFICATION_CACHE_TTL,
                    json.dumps(cache_data, default=str)
                )
            
            return notification_list
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            raise

    @staticmethod
    async def get_notification_count(
        session: AsyncSession,
        user_id: UUIDType,
        notification_type: Optional[NotificationType] = None,
        unread_only: bool = False
    ) -> int:
        """Get total count of notifications for a user."""
        try:
            # Build cache key
            cache_key = f"notification_count:{user_id}:{notification_type}:{unread_only}"
            
            # Try cache first
            cached = await redis_client.get(cache_key)
            if cached:
                try:
                    return int(cached)
                except ValueError:
                    pass
            
            # Build query
            stmt = select(func.count(Notification.notification_id)).where(
                Notification.user_id == user_id
            )
            
            # Apply filters
            if notification_type:
                stmt = stmt.where(Notification.type == notification_type)
            
            if unread_only:
                stmt = stmt.where(Notification.is_read == False)
            
            result = await session.execute(stmt)
            count = result.scalar() or 0
            
            # Cache the result
            await redis_client.setex(cache_key, NOTIFICATION_COUNT_CACHE_TTL, count)
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting notification count: {e}")
            raise

    @staticmethod
    async def mark_as_read(
        session: AsyncSession,
        notification_id: UUIDType,
        user_id: UUIDType
    ) -> bool:
        """Mark a specific notification as read."""
        try:
            # Update notification
            stmt = (
                update(Notification)
                .where(
                    and_(
                        Notification.notification_id == notification_id,
                        Notification.user_id == user_id
                    )
                )
                .values(
                    is_read=True,
                    updated_at=datetime.utcnow()
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            # Check if any rows were updated
            if result.rowcount > 0:
                # Invalidate cache
                await NotificationService._invalidate_user_cache(user_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def mark_all_as_read(
        session: AsyncSession,
        user_id: UUIDType,
        notification_type: Optional[NotificationType] = None
    ) -> int:
        """Mark all notifications as read for a user."""
        try:
            # Build update statement
            stmt = (
                update(Notification)
                .where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False
                    )
                )
                .values(
                    is_read=True,
                    updated_at=datetime.utcnow()
                )
            )
            
            # Apply type filter if specified
            if notification_type:
                stmt = stmt.where(Notification.type == notification_type)
            
            result = await session.execute(stmt)
            await session.commit()
            
            # Invalidate cache
            await NotificationService._invalidate_user_cache(user_id)
            
            return result.rowcount
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def delete_notification(
        session: AsyncSession,
        notification_id: UUIDType,
        user_id: UUIDType
    ) -> bool:
        """Delete a specific notification."""
        try:
            # Delete notification
            stmt = delete(Notification).where(
                and_(
                    Notification.notification_id == notification_id,
                    Notification.user_id == user_id
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            # Check if any rows were deleted
            if result.rowcount > 0:
                # Invalidate cache
                await NotificationService._invalidate_user_cache(user_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def delete_user_notifications(
        session: AsyncSession,
        user_id: UUIDType,
        notification_type: Optional[NotificationType] = None,
        read_only: bool = False
    ) -> int:
        """Delete notifications for a user with filtering."""
        try:
            # Build delete statement
            stmt = delete(Notification).where(Notification.user_id == user_id)
            
            # Apply filters
            if notification_type:
                stmt = stmt.where(Notification.type == notification_type)
            
            if read_only:
                stmt = stmt.where(Notification.is_read == True)
            
            result = await session.execute(stmt)
            await session.commit()
            
            # Invalidate cache
            await NotificationService._invalidate_user_cache(user_id)
            
            return result.rowcount
            
        except Exception as e:
            logger.error(f"Error deleting user notifications: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def create_notification(
        session: AsyncSession,
        user_id: UUIDType,
        notification_type: NotificationType,
        content: Dict[str, Any],
        status: NotificationStatus = NotificationStatus.PENDING
    ) -> Notification:
        """Create a new notification."""
        try:
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                content=json.dumps(content),
                status=status
            )
            
            session.add(notification)
            await session.commit()
            await session.refresh(notification)
            
            # Invalidate cache
            await NotificationService._invalidate_user_cache(user_id)
            
            return notification
            
        except IntegrityError:
            await session.rollback()
            raise ValueError("Failed to create notification")

    @staticmethod
    async def update_notification_status(
        session: AsyncSession,
        notification_id: UUIDType,
        status: NotificationStatus
    ) -> bool:
        """Update the status of a notification."""
        try:
            stmt = (
                update(Notification)
                .where(Notification.notification_id == notification_id)
                .values(
                    status=status,
                    updated_at=datetime.utcnow()
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                # Get the notification to invalidate user cache
                notification = await session.get(Notification, notification_id)
                if notification:
                    await NotificationService._invalidate_user_cache(notification.user_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating notification status: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_user_preferences(
        session: AsyncSession,
        user_id: UUIDType
    ) -> Dict[str, Any]:
        """Get notification preferences for a user."""
        try:
            # Get user from database
            user = await session.get(User, user_id)
            if not user:
                raise ValueError("User not found")
            
            # Return preferences (assuming these fields exist on User model)
            preferences = {
                "email_notifications": getattr(user, 'email_notifications', True),
                "push_notifications": getattr(user, 'push_notifications', True),
                "new_message_notifications": getattr(user, 'new_message_notifications', True),
                "room_invite_notifications": getattr(user, 'room_invite_notifications', True)
            }
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            raise

    @staticmethod
    async def update_user_preferences(
        session: AsyncSession,
        user_id: UUIDType,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update notification preferences for a user."""
        try:
            # Update user preferences
            stmt = (
                update(User)
                .where(User.user_id == user_id)
                .values(**preferences)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount == 0:
                raise ValueError("User not found")
            
            # Return updated preferences
            return await NotificationService.get_user_preferences(session, user_id)
            
        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            await session.rollback()
            raise

    @staticmethod
    async def get_notifications_by_type(
        session: AsyncSession,
        user_id: UUIDType,
        notification_type: NotificationType,
        limit: int = 10
    ) -> List[NotificationGet]:
        """Get recent notifications of a specific type for a user."""
        return await NotificationService.get_user_notifications(
            session=session,
            user_id=user_id,
            limit=limit,
            notification_type=notification_type
        )

    @staticmethod
    async def _invalidate_user_cache(user_id: UUIDType) -> None:
        """Invalidate all cached data for a user."""
        try:
            # Pattern to match all cache keys for this user
            patterns = [
                f"user_notifications:{user_id}:*",
                f"notification_count:{user_id}:*"
            ]
            
            for pattern in patterns:
                keys = []
                async for key in redis_client.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    await redis_client.delete(*keys)
                    
        except Exception as e:
            logger.error(f"Error invalidating user cache: {e}")
            # Don't raise - cache invalidation failure shouldn't break the operation
