"""
Integration functions for the notification service.
These functions help other services create notifications and publish them to RabbitMQ.
"""

from typing import Dict, Any, List
from uuid import UUID as UUIDType
import logging

from realtime_messaging.services.rabbitmq import publish_message_notification, rabbitmq_service
from realtime_messaging.services.notification_service import NotificationService
from realtime_messaging.models.notification import NotificationType, NotificationStatus
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


async def create_message_notification(
    session: AsyncSession,
    message_id: UUIDType,
    room_id: UUIDType,
    sender_id: UUIDType,
    recipient_ids: List[UUIDType],
    message_content: str,
    sender_info: Dict[str, Any]
) -> bool:
    """
    Create and publish a new message notification.
    
    This function is called by the message service when a new message is created.
    """
    try:
        # Publish to RabbitMQ for async processing
        success = await publish_message_notification(
            message_id=message_id,
            room_id=room_id,
            sender_id=sender_id,
            recipient_ids=recipient_ids,
            message_content=message_content,
            sender_info=sender_info
        )
        
        if success:
            logger.info(f"Successfully published message notification for message {message_id}")
            return True
        else:
            # Fallback: create notifications directly in database
            logger.warning(f"Failed to publish to RabbitMQ, creating notifications directly")
            return await _create_message_notifications_fallback(
                session, message_id, room_id, sender_info, message_content, recipient_ids
            )
            
    except Exception as e:
        logger.error(f"Error creating message notification: {e}")
        # Try fallback
        return await _create_message_notifications_fallback(
            session, message_id, room_id, sender_info, message_content, recipient_ids
        )


async def create_room_invite_notification(
    session: AsyncSession,
    room_id: UUIDType,
    room_name: str,
    room_description: str,
    inviter_id: UUIDType,
    invitee_id: UUIDType,
    inviter_info: Dict[str, Any]
) -> bool:
    """
    Create and publish a room invitation notification.
    
    This function is called by the room service when a user is invited to a room.
    """
    try:
        # Prepare data for RabbitMQ
        invite_data = {
            "type": "room_invite",
            "invitee_id": str(invitee_id),
            "inviter_info": inviter_info,
            "room_info": {
                "room_id": str(room_id),
                "name": room_name,
                "description": room_description
            }
        }
        
        # Publish to RabbitMQ
        success = await rabbitmq_service.publish_message_notification(
            invite_data,
            routing_key="notification.room.invite"
        )
        
        if success:
            logger.info(f"Successfully published room invite notification for room {room_id}")
            return True
        else:
            # Fallback: create notification directly
            logger.warning(f"Failed to publish room invite to RabbitMQ, creating notification directly")
            return await _create_room_invite_notification_fallback(
                session, room_id, room_name, inviter_info, invitee_id
            )
            
    except Exception as e:
        logger.error(f"Error creating room invite notification: {e}")
        # Try fallback
        return await _create_room_invite_notification_fallback(
            session, room_id, room_name, inviter_info, invitee_id
        )


async def create_friend_request_notification(
    session: AsyncSession,
    sender_id: UUIDType,
    recipient_id: UUIDType,
    sender_info: Dict[str, Any],
    request_type: str = "friend_request"
) -> bool:
    """
    Create and publish a friend request notification.
    
    This function would be called by a friend service when friend requests are sent/accepted.
    """
    try:
        # Prepare data for RabbitMQ
        friend_request_data = {
            "type": "friend_request",
            "recipient_id": str(recipient_id),
            "sender_info": sender_info,
            "request_type": request_type
        }
        
        # Publish to RabbitMQ
        success = await rabbitmq_service.publish_message_notification(
            friend_request_data,
            routing_key="notification.friend.request"
        )
        
        if success:
            logger.info(f"Successfully published friend request notification")
            return True
        else:
            # Fallback: create notification directly
            logger.warning(f"Failed to publish friend request to RabbitMQ, creating notification directly")
            return await _create_friend_request_notification_fallback(
                session, sender_info, recipient_id, request_type
            )
            
    except Exception as e:
        logger.error(f"Error creating friend request notification: {e}")
        # Try fallback
        return await _create_friend_request_notification_fallback(
            session, sender_info, recipient_id, request_type
        )


# Fallback functions for direct database creation
async def _create_message_notifications_fallback(
    session: AsyncSession,
    message_id: UUIDType,
    room_id: UUIDType,
    sender_info: Dict[str, Any],
    message_content: str,
    recipient_ids: List[UUIDType]
) -> bool:
    """Fallback method to create message notifications directly in database."""
    try:
        success_count = 0
        
        for recipient_id in recipient_ids:
            notification_content = {
                "message_id": str(message_id),
                "room_id": str(room_id),
                "sender_id": sender_info.get("user_id"),
                "sender_username": sender_info.get("username"),
                "sender_display_name": sender_info.get("display_name"),
                "message_preview": (
                    message_content[:100] + "..." 
                    if len(message_content) > 100 
                    else message_content
                )
            }
            
            try:
                await NotificationService.create_notification(
                    session=session,
                    user_id=recipient_id,
                    notification_type=NotificationType.NEW_MESSAGE,
                    content=notification_content,
                    status=NotificationStatus.PENDING
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to create notification for user {recipient_id}: {e}")
        
        logger.info(f"Created {success_count}/{len(recipient_ids)} notifications as fallback")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error in message notification fallback: {e}")
        return False


async def _create_room_invite_notification_fallback(
    session: AsyncSession,
    room_id: UUIDType,
    room_name: str,
    inviter_info: Dict[str, Any],
    invitee_id: UUIDType
) -> bool:
    """Fallback method to create room invite notification directly in database."""
    try:
        notification_content = {
            "room_id": str(room_id),
            "room_name": room_name,
            "inviter_id": inviter_info.get("user_id"),
            "inviter_username": inviter_info.get("username"),
            "inviter_display_name": inviter_info.get("display_name"),
            "message": f"invited you to join {room_name}"
        }
        
        await NotificationService.create_notification(
            session=session,
            user_id=invitee_id,
            notification_type=NotificationType.ROOM_INVITATION,
            content=notification_content,
            status=NotificationStatus.PENDING
        )
        
        logger.info(f"Created room invite notification as fallback")
        return True
        
    except Exception as e:
        logger.error(f"Error in room invite notification fallback: {e}")
        return False


async def _create_friend_request_notification_fallback(
    session: AsyncSession,
    sender_info: Dict[str, Any],
    recipient_id: UUIDType,
    request_type: str
) -> bool:
    """Fallback method to create friend request notification directly in database."""
    try:
        if request_type == "friend_request":
            message = f"{sender_info.get('display_name', sender_info.get('username'))} sent you a friend request"
            notification_type = NotificationType.FRIEND_REQUEST
        else:  # friend_request_accepted
            message = f"{sender_info.get('display_name', sender_info.get('username'))} accepted your friend request"
            notification_type = NotificationType.FRIEND_REQUEST_ACCEPTED
        
        notification_content = {
            "sender_id": sender_info.get("user_id"),
            "sender_username": sender_info.get("username"),
            "sender_display_name": sender_info.get("display_name"),
            "request_type": request_type,
            "message": message
        }
        
        await NotificationService.create_notification(
            session=session,
            user_id=recipient_id,
            notification_type=notification_type,
            content=notification_content,
            status=NotificationStatus.PENDING
        )
        
        logger.info(f"Created friend request notification as fallback")
        return True
        
    except Exception as e:
        logger.error(f"Error in friend request notification fallback: {e}")
        return False


# Utility functions
async def get_user_notification_summary(
    session: AsyncSession,
    user_id: UUIDType
) -> Dict[str, Any]:
    """Get a summary of notifications for a user."""
    try:
        # Get total counts
        total_count = await NotificationService.get_notification_count(
            session, user_id
        )
        
        unread_count = await NotificationService.get_notification_count(
            session, user_id, unread_only=True
        )
        
        # Get counts by type
        message_count = await NotificationService.get_notification_count(
            session, user_id, notification_type=NotificationType.NEW_MESSAGE, unread_only=True
        )
        
        invite_count = await NotificationService.get_notification_count(
            session, user_id, notification_type=NotificationType.ROOM_INVITATION, unread_only=True
        )
        
        friend_request_count = await NotificationService.get_notification_count(
            session, user_id, notification_type=NotificationType.FRIEND_REQUEST, unread_only=True
        )
        
        return {
            "total_notifications": total_count,
            "unread_notifications": unread_count,
            "unread_by_type": {
                "new_messages": message_count,
                "room_invitations": invite_count,
                "friend_requests": friend_request_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting notification summary: {e}")
        return {
            "total_notifications": 0,
            "unread_notifications": 0,
            "unread_by_type": {
                "new_messages": 0,
                "room_invitations": 0,
                "friend_requests": 0
            }
        }


async def mark_message_notifications_as_read(
    session: AsyncSession,
    user_id: UUIDType,
    room_id: UUIDType
) -> int:
    """Mark all message notifications for a specific room as read."""
    try:
        # This would require a more specific query to filter by room_id in content
        # For now, mark all new message notifications as read
        return await NotificationService.mark_all_as_read(
            session=session,
            user_id=user_id,
            notification_type=NotificationType.NEW_MESSAGE
        )
        
    except Exception as e:
        logger.error(f"Error marking message notifications as read: {e}")
        return 0
