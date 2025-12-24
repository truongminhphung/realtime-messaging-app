from typing import List, Optional, Dict, Any
from uuid import UUID as UUIDType
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.exc import IntegrityError
import redis.asyncio as redis

from realtime_messaging.models.message import (
    Message,
    MessageCreateInternal,
    MessageWithSenderInfo,
)
from realtime_messaging.models.user import User
from realtime_messaging.services.room_service import RoomService
from realtime_messaging.config import settings


# Configure logging
logger = logging.getLogger(__name__)

# Redis client for caching and rate limiting
redis_client = redis.from_url(settings.redis_url)

# Constants
MESSAGES_CACHE_TTL = 600  # 10 minutes
RECENT_MESSAGES_LIMIT = 50
RATE_LIMIT_MESSAGES = 10  # messages per minute
RATE_LIMIT_WINDOW = 60  # seconds


class MessageService:
    """Service class for message operations."""

    @staticmethod
    async def create_message(
        session: AsyncSession, message_data: MessageCreateInternal
    ) -> Message:
        """Create a new message in the database."""
        try:
            # Validation is now handled by Pydantic in MessageCreateInternal model
            # Create message (content is already validated and cleaned by Pydantic)
            message = Message(
                room_id=message_data.room_id,
                sender_id=message_data.sender_id,
                content=message_data.content,  # Already cleaned by Pydantic validator
            )

            session.add(message)
            await session.commit()
            await session.refresh(message)

            # Invalidate cache for this room
            await MessageService._invalidate_room_messages_cache(message_data.room_id)

            return message

        except IntegrityError:
            await session.rollback()
            raise ValueError("Failed to create message")

    @staticmethod
    async def get_room_messages(
        session: AsyncSession,
        room_id: UUIDType,
        limit: int = RECENT_MESSAGES_LIMIT,
        offset: int = 0,
        use_cache: bool = True,
    ) -> List[MessageWithSenderInfo]:
        """Get recent messages for a room with sender information."""
        cache_key = f"room_messages:{room_id}:{limit}:{offset}"
        # Try to get from cache first
        if use_cache:
            cached = await redis_client.get(cache_key)
            if cached:
                try:
                    cached_data = json.loads(cached)
                    return [MessageWithSenderInfo(**msg) for msg in cached_data]
                except (json.JSONDecodeError, ValueError):
                    pass

        # Get from database with sender info
        stmt = (
            select(Message, User)
            .join(User, Message.sender_id == User.user_id)
            .where(Message.room_id == room_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
            .offset(offset)
        )

        result = await session.execute(stmt)
        messages = []

        for message, user in result.all():
            message_data = MessageWithSenderInfo(
                message_id=message.message_id,
                room_id=message.room_id,
                sender_id=message.sender_id,
                sender_username=user.username,
                sender_display_name=user.display_name,
                # sender_profile_picture_url=user.profile_picture_url,
                content=message.content,
                created_at=message.created_at,
            )
            messages.append(message_data)

        # Reverse to get chronological order (oldest first)
        messages.reverse()

        # Cache the result
        if use_cache and messages:
            cache_data = [msg.model_dump(mode="json") for msg in messages]
            await redis_client.setex(
                cache_key, MESSAGES_CACHE_TTL, json.dumps(cache_data, default=str)
            )

        return messages

    @staticmethod
    async def get_message_by_id(
        session: AsyncSession, message_id: UUIDType
    ) -> Optional[Message]:
        """Get a specific message by ID."""
        stmt = select(Message).where(Message.message_id == message_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_message(
        session: AsyncSession, message_id: UUIDType, user_id: UUIDType, content: str
    ) -> Optional[Message]:
        """Update message content (only sender can update)."""
        try:
            message = await MessageService.get_message_by_id(session, message_id)
            if not message:
                return None

            # Only sender can update message
            if message.sender_id != user_id:
                raise ValueError("Only message sender can update message")

            # Validation is handled by Pydantic when this method is called from the API layer
            # If called directly, we should validate using MessageUpdate model
            from realtime_messaging.models.message import MessageUpdate

            validated_data = MessageUpdate(content=content)

            # Update message with validated content
            message.content = validated_data.content
            await session.commit()
            await session.refresh(message)

            # Invalidate cache
            await MessageService._invalidate_room_messages_cache(message.room_id)

            return message

        except ValueError:
            raise
        except Exception:
            await session.rollback()
            raise ValueError("Failed to update message")

    @staticmethod
    async def delete_message(
        session: AsyncSession, message_id: UUIDType, user_id: UUIDType
    ) -> bool:
        """Delete a message (only sender can delete)."""
        try:
            message = await MessageService.get_message_by_id(session, message_id)
            if not message:
                return False

            # Only sender can delete message
            if message.sender_id != user_id:
                raise ValueError("Only message sender can delete message")

            room_id = message.room_id
            await session.delete(message)
            await session.commit()

            # Invalidate cache
            await MessageService._invalidate_room_messages_cache(room_id)

            return True

        except ValueError:
            raise
        except Exception:
            await session.rollback()
            raise ValueError("Failed to delete message")

    @staticmethod
    async def check_rate_limit(user_id: UUIDType) -> bool:
        """Check if user is within rate limit for sending messages."""
        rate_limit_key = f"rate_limit:messages:{user_id}"

        try:
            # Get current count
            current_count = await redis_client.get(rate_limit_key)

            if current_count is None:
                # First message in the window
                await redis_client.setex(rate_limit_key, RATE_LIMIT_WINDOW, 1)
                return True

            count = int(current_count)
            if count >= RATE_LIMIT_MESSAGES:
                return False

            # Increment counter
            await redis_client.incr(rate_limit_key)
            return True

        except Exception:
            # If Redis fails, allow the message (graceful degradation)
            return True

    @staticmethod
    async def get_rate_limit_info(user_id: UUIDType) -> Dict[str, Any]:
        """Get rate limit information for a user."""
        rate_limit_key = f"rate_limit:messages:{user_id}"

        try:
            current_count = await redis_client.get(rate_limit_key)
            ttl = await redis_client.ttl(rate_limit_key)

            if current_count is None:
                return {
                    "messages_sent": 0,
                    "messages_remaining": RATE_LIMIT_MESSAGES,
                    "reset_in_seconds": 0,
                    "limit": RATE_LIMIT_MESSAGES,
                }

            count = int(current_count)
            return {
                "messages_sent": count,
                "messages_remaining": max(0, RATE_LIMIT_MESSAGES - count),
                "reset_in_seconds": max(0, ttl),
                "limit": RATE_LIMIT_MESSAGES,
            }

        except Exception:
            # Default response if Redis fails
            return {
                "messages_sent": 0,
                "messages_remaining": RATE_LIMIT_MESSAGES,
                "reset_in_seconds": 0,
                "limit": RATE_LIMIT_MESSAGES,
            }

    @staticmethod
    async def validate_message_access(
        session: AsyncSession, room_id: UUIDType, user_id: UUIDType
    ) -> bool:
        """Validate that user has access to send/receive messages in room."""
        return await RoomService.is_user_participant(session, room_id, user_id)

    @staticmethod
    async def get_room_message_count(session: AsyncSession, room_id: UUIDType) -> int:
        """Get total message count for a room."""
        stmt = select(Message).where(Message.room_id == room_id)
        result = await session.execute(stmt)
        return len(list(result.scalars().all()))

    @staticmethod
    async def search_messages(
        session: AsyncSession, room_id: UUIDType, query: str, limit: int = 20
    ) -> List[MessageWithSenderInfo]:
        """Search messages in a room by content."""
        if not query or len(query.strip()) < 2:
            return []

        # Simple text search (can be enhanced with full-text search)
        stmt = (
            select(Message, User)
            .join(User, Message.sender_id == User.user_id)
            .where(
                and_(
                    Message.room_id == room_id,
                    Message.content.ilike(f"%{query.strip()}%"),
                )
            )
            .order_by(desc(Message.created_at))
            .limit(limit)
        )

        result = await session.execute(stmt)
        messages = []

        for message, user in result.all():
            message_data = MessageWithSenderInfo(
                message_id=message.message_id,
                room_id=message.room_id,
                sender_id=message.sender_id,
                sender_username=user.username,
                sender_display_name=user.display_name,
                sender_profile_picture_url=user.profile_picture_url,
                content=message.content,
                created_at=message.created_at,
            )
            messages.append(message_data)

        return messages

    @staticmethod
    async def get_messages_after(
        session: AsyncSession,
        room_id: UUIDType,
        after_message_id: UUIDType,
        limit: int = 50,
    ) -> List[MessageWithSenderInfo]:
        """Get messages after a specific message ID (for pagination)."""
        # First get the timestamp of the reference message
        ref_stmt = select(Message.created_at).where(
            Message.message_id == after_message_id
        )
        ref_result = await session.execute(ref_stmt)
        ref_timestamp = ref_result.scalar_one_or_none()

        if not ref_timestamp:
            return []

        # Get messages after that timestamp
        stmt = (
            select(Message, User)
            .join(User, Message.sender_id == User.user_id)
            .where(and_(Message.room_id == room_id, Message.created_at > ref_timestamp))
            .order_by(Message.created_at.asc())
            .limit(limit)
        )

        result = await session.execute(stmt)
        messages = []

        for message, user in result.all():
            message_data = MessageWithSenderInfo(
                message_id=message.message_id,
                room_id=message.room_id,
                sender_id=message.sender_id,
                sender_username=user.username,
                sender_display_name=user.display_name,
                sender_profile_picture_url=user.profile_picture_url,
                content=message.content,
                created_at=message.created_at,
            )
            messages.append(message_data)

        return messages

    @staticmethod
    async def _invalidate_room_messages_cache(room_id: UUIDType) -> None:
        """Invalidate all cached message data for a room."""
        try:
            # Pattern to match all cache keys for this room
            pattern = f"room_messages:{room_id}:*"

            # Get all matching keys
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            # Delete all matching keys
            if keys:
                await redis_client.delete(*keys)

        except Exception:
            # If cache invalidation fails, continue (cache will expire naturally)
            pass

    @staticmethod
    async def create_message_notification(
        session: AsyncSession, message: Message, room_participants: List[UUIDType]
    ) -> None:
        """Create notifications for new messages (excluding sender)."""
        from realtime_messaging.services.rabbitmq import publish_message_notification

        try:
            # Get sender info for notification
            sender = await session.get(User, message.sender_id)
            if not sender:
                return

            # Get recipient IDs (all participants except sender)
            recipient_ids = [
                pid for pid in room_participants if pid != message.sender_id
            ]

            if not recipient_ids:
                return

            # Prepare sender info
            sender_info = {
                "user_id": str(sender.user_id),
                "username": sender.username,
                "display_name": sender.display_name,
                "profile_picture_url": sender.profile_picture_url,
            }

            # Publish to RabbitMQ for async processing
            success = await publish_message_notification(
                message_id=message.message_id,
                room_id=message.room_id,
                sender_id=message.sender_id,
                recipient_ids=recipient_ids,
                message_content=message.content,
                sender_info=sender_info,
            )

            if success:
                logger.info(
                    f"Published notification for message {message.message_id} to RabbitMQ"
                )
            else:
                logger.error(
                    f"Failed to publish notification for message {message.message_id}"
                )
                # Fallback: create notifications directly
                await MessageService._create_notifications_fallback(
                    session, message, recipient_ids, sender_info
                )

        except Exception as e:
            logger.error(f"Error creating message notification: {e}")
            # Don't fail message creation if notification fails
            pass

    @staticmethod
    async def _create_notifications_fallback(
        session: AsyncSession,
        message: Message,
        recipient_ids: List[UUIDType],
        sender_info: Dict[str, Any],
    ) -> None:
        """Fallback method to create notifications directly in database."""
        from realtime_messaging.models.notification import (
            Notification,
            NotificationType,
            NotificationStatus,
        )

        try:
            notifications = []
            for recipient_id in recipient_ids:
                notification = Notification(
                    user_id=recipient_id,
                    type=NotificationType.NEW_MESSAGE,
                    content=json.dumps(
                        {
                            "message_id": str(message.message_id),
                            "room_id": str(message.room_id),
                            "sender_id": str(message.sender_id),
                            "sender_username": sender_info["username"],
                            "sender_display_name": sender_info["display_name"],
                            "message_preview": (
                                message.content[:100] + "..."
                                if len(message.content) > 100
                                else message.content
                            ),
                        }
                    ),
                    status=NotificationStatus.PENDING,
                )
                notifications.append(notification)

            if notifications:
                session.add_all(notifications)
                await session.commit()
                logger.info(f"Created {len(notifications)} notifications as fallback")

        except Exception as e:
            logger.error(f"Error in notification fallback: {e}")
            # Don't fail even in fallback
