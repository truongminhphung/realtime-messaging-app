import asyncio
import json
import logging
from typing import Dict, Any, List
from uuid import UUID as UUIDType

from sqlalchemy.ext.asyncio import AsyncSession

from realtime_messaging.db.depends import sessionmanager
from realtime_messaging.models.notification import Notification, NotificationType, NotificationStatus
from realtime_messaging.models.user import User
from realtime_messaging.services.rabbitmq import rabbitmq_service, NOTIFICATION_QUEUE


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationWorker:
    """Worker to process notifications from RabbitMQ."""
    
    def __init__(self):
        self.running = False
    
    async def start(self) -> None:
        """Start the notification worker."""
        try:
            # Connect to RabbitMQ
            await rabbitmq_service.connect()
            
            # Start consuming notifications
            await rabbitmq_service.consume_notifications(
                callback=self.process_notification,
                queue_name=NOTIFICATION_QUEUE
            )
            
            self.running = True
            logger.info("Notification worker started")
            
            # Keep the worker running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting notification worker: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the notification worker."""
        self.running = False
        await rabbitmq_service.disconnect()
        logger.info("Notification worker stopped")
    
    async def process_notification(self, data: Dict[str, Any]) -> bool:
        """Process a notification message from RabbitMQ."""
        try:
            logger.info(f"Processing notification: {data.get('type', 'unknown')}")
            
            notification_type = data.get("type")
            
            if notification_type == "new_message":
                return await self._process_message_notification(data)
            elif notification_type == "room_invite":
                return await self._process_room_invite_notification(data)
            elif notification_type == "friend_request":
                return await self._process_friend_request_notification(data)
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
                return True  # Acknowledge unknown types to avoid reprocessing
                
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            return False  # This will cause requeue/retry
    
    async def _process_message_notification(self, data: Dict[str, Any]) -> bool:
        """Process a new message notification."""
        try:
            # Extract data
            message_id = data.get("message_id")
            room_id = data.get("room_id")
            sender_id = data.get("sender_id")
            recipient_ids = data.get("recipient_ids", [])
            message_content = data.get("message_content", "")
            sender_info = data.get("sender_info", {})
            
            if not all([message_id, room_id, sender_id, recipient_ids]):
                logger.error("Missing required fields in message notification")
                return True  # Don't requeue malformed messages
            
            # Convert string IDs back to UUIDs
            recipient_uuids = [UUIDType(rid) for rid in recipient_ids]
            
            # Create notifications in database
            async for session in sessionmanager.get_session():
                success = await self._create_database_notifications(
                    session, message_id, room_id, sender_info, 
                    message_content, recipient_uuids
                )
                
                if success:
                    # Send push notifications (if configured)
                    await self._send_push_notifications(
                        session, recipient_uuids, sender_info, message_content
                    )
                    
                    # Send email notifications (if configured)
                    await self._send_email_notifications(
                        session, recipient_uuids, sender_info, message_content, room_id
                    )
                
                return success
                
        except Exception as e:
            logger.error(f"Error processing message notification: {e}")
            return False
    
    async def _create_database_notifications(
        self,
        session: AsyncSession,
        message_id: str,
        room_id: str,
        sender_info: Dict[str, Any],
        message_content: str,
        recipient_ids: List[UUIDType]
    ) -> bool:
        """Create notification records in the database."""
        try:
            notifications = []
            
            for recipient_id in recipient_ids:
                # Create notification content
                notification_content = {
                    "message_id": message_id,
                    "room_id": room_id,
                    "sender_id": sender_info.get("user_id"),
                    "sender_username": sender_info.get("username"),
                    "sender_display_name": sender_info.get("display_name"),
                    "message_preview": (
                        message_content[:100] + "..." 
                        if len(message_content) > 100 
                        else message_content
                    )
                }
                
                notification = Notification(
                    user_id=recipient_id,
                    type=NotificationType.NEW_MESSAGE,
                    content=json.dumps(notification_content),
                    status=NotificationStatus.PENDING
                )
                notifications.append(notification)
            
            if notifications:
                session.add_all(notifications)
                await session.commit()
                logger.info(f"Created {len(notifications)} database notifications")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating database notifications: {e}")
            await session.rollback()
            return False
    
    async def _send_push_notifications(
        self,
        session: AsyncSession,
        recipient_ids: List[UUIDType],
        sender_info: Dict[str, Any],
        message_content: str
    ) -> None:
        """Send push notifications to mobile devices."""
        try:
            # Get users with push tokens and push notifications enabled
            from sqlalchemy import select
            
            stmt = select(User).where(
                User.user_id.in_(recipient_ids),
                User.push_token.isnot(None)
                # Add push notification preference check if available
                # User.push_notifications.is_(True)
            )
            result = await session.execute(stmt)
            users_with_push = result.scalars().all()
            
            successful_sends = 0
            failed_sends = 0
            
            for user in users_with_push:
                try:
                    # Check user preferences (implement if user preferences are available)
                    user_wants_push = getattr(user, 'push_notifications', True)
                    user_wants_message_notifications = getattr(user, 'new_message_notifications', True)
                    
                    if not (user_wants_push and user_wants_message_notifications):
                        logger.info(f"User {user.username} has push notifications disabled")
                        continue
                    
                    # Prepare push notification data
                    push_data = {
                        "title": f"New message from {sender_info.get('display_name', sender_info.get('username'))}",
                        "body": message_content[:100] + "..." if len(message_content) > 100 else message_content,
                        "data": {
                            "type": "new_message",
                            "room_id": sender_info.get("room_id"),
                            "sender_id": sender_info.get("user_id"),
                            "click_action": "FLUTTER_NOTIFICATION_CLICK"
                        },
                        "token": user.push_token
                    }
                    
                    # Send push notification (implement actual sending here)
                    success = await self._send_fcm_notification(push_data)
                    
                    if success:
                        successful_sends += 1
                        logger.info(f"✅ Sent push notification to {user.username}")
                    else:
                        failed_sends += 1
                        logger.warning(f"❌ Failed to send push notification to {user.username}")
                        
                except Exception as e:
                    failed_sends += 1
                    logger.error(f"Error sending push notification to {user.username}: {e}")
            
            logger.info(f"Push notification summary: {successful_sends} sent, {failed_sends} failed")
                
        except Exception as e:
            logger.error(f"Error sending push notifications: {e}")
    
    async def _send_fcm_notification(self, push_data: Dict[str, Any]) -> bool:
        """Send push notification via Firebase Cloud Messaging."""
        try:
            # TODO: Implement actual FCM sending
            # This would use the Firebase Admin SDK or HTTP API
            
            # Example implementation:
            # import firebase_admin
            # from firebase_admin import messaging
            # 
            # message = messaging.Message(
            #     notification=messaging.Notification(
            #         title=push_data["title"],
            #         body=push_data["body"]
            #     ),
            #     data=push_data["data"],
            #     token=push_data["token"]
            # )
            # 
            # response = messaging.send(message)
            # return True if response else False
            
            # For now, simulate sending
            logger.debug(f"FCM Push notification data: {push_data}")
            
            # Simulate 95% success rate
            import random
            return random.random() < 0.95
            
        except Exception as e:
            logger.error(f"FCM sending error: {e}")
            return False
    
    async def _send_email_notifications(
        self,
        session: AsyncSession,
        recipient_ids: List[UUIDType],
        sender_info: Dict[str, Any],
        message_content: str,
        room_id: str
    ) -> None:
        """Send email notifications for users who prefer email."""
        try:
            # Get users who want email notifications
            from sqlalchemy import select
            
            stmt = select(User).where(
                User.user_id.in_(recipient_ids)
                # Add email notification preference check if available
                # User.email_notifications.is_(True)
            )
            result = await session.execute(stmt)
            users_with_email = result.scalars().all()
            
            successful_sends = 0
            failed_sends = 0
            
            for user in users_with_email:
                try:
                    # Check user preferences
                    user_wants_email = getattr(user, 'email_notifications', True)
                    user_wants_message_notifications = getattr(user, 'new_message_notifications', True)
                    
                    if not (user_wants_email and user_wants_message_notifications):
                        logger.info(f"User {user.username} has email notifications disabled")
                        continue
                    
                    # Prepare email data
                    email_data = {
                        "to": user.email,
                        "subject": f"New message from {sender_info.get('display_name', sender_info.get('username'))}",
                        "template": "new_message",
                        "template_data": {
                            "recipient_name": user.display_name or user.username,
                            "sender_name": sender_info.get('display_name', sender_info.get('username')),
                            "message_content": message_content,
                            "room_id": room_id,
                            "app_url": "https://your-app.com"  # Configure this
                        }
                    }
                    
                    # Send email notification
                    success = await self._send_email_via_service(email_data)
                    
                    if success:
                        successful_sends += 1
                        logger.info(f"✅ Sent email notification to {user.email}")
                    else:
                        failed_sends += 1
                        logger.warning(f"❌ Failed to send email notification to {user.email}")
                        
                except Exception as e:
                    failed_sends += 1
                    logger.error(f"Error sending email notification to {user.email}: {e}")
            
            logger.info(f"Email notification summary: {successful_sends} sent, {failed_sends} failed")
                
        except Exception as e:
            logger.error(f"Error sending email notifications: {e}")
    
    async def _send_email_via_service(self, email_data: Dict[str, Any]) -> bool:
        """Send email via email service (SendGrid, SES, etc.)."""
        try:
            # TODO: Implement actual email sending
            # This would integrate with services like SendGrid, AWS SES, etc.
            
            # Example SendGrid implementation:
            # import sendgrid
            # from sendgrid.helpers.mail import Mail
            # 
            # sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
            # message = Mail(
            #     from_email='notifications@your-app.com',
            #     to_emails=email_data["to"],
            #     subject=email_data["subject"],
            #     html_content=render_template(email_data["template"], email_data["template_data"])
            # )
            # 
            # response = sg.send(message)
            # return response.status_code == 202
            
            # For now, simulate sending
            logger.debug(f"Email notification data: {email_data}")
            
            # Simulate 98% success rate
            import random
            return random.random() < 0.98
            
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            return False
    
    async def _send_room_invite_notifications(
        self,
        session: AsyncSession,
        invite_data: Dict[str, Any]
    ) -> None:
        """Send notifications for room invitations."""
        try:
            invitee_id = UUIDType(invite_data.get("invitee_id"))
            inviter_info = invite_data.get("inviter_info", {})
            room_info = invite_data.get("room_info", {})
            
            # Get the invitee user
            invitee = await session.get(User, invitee_id)
            if not invitee:
                logger.error(f"Invitee user not found: {invitee_id}")
                return
            
            # Check if user wants room invite notifications
            user_wants_invites = getattr(invitee, 'room_invite_notifications', True)
            if not user_wants_invites:
                logger.info(f"User {invitee.username} has room invite notifications disabled")
                return
            
            # Send push notification
            if getattr(invitee, 'push_notifications', True) and invitee.push_token:
                push_data = {
                    "title": "Room Invitation",
                    "body": f"{inviter_info.get('display_name', inviter_info.get('username'))} invited you to {room_info.get('name')}",
                    "data": {
                        "type": "room_invite",
                        "room_id": room_info.get("room_id"),
                        "inviter_id": inviter_info.get("user_id")
                    },
                    "token": invitee.push_token
                }
                await self._send_fcm_notification(push_data)
            
            # Send email notification
            if getattr(invitee, 'email_notifications', True):
                email_data = {
                    "to": invitee.email,
                    "subject": f"You're invited to join {room_info.get('name')}",
                    "template": "room_invitation",
                    "template_data": {
                        "invitee_name": invitee.display_name or invitee.username,
                        "inviter_name": inviter_info.get('display_name', inviter_info.get('username')),
                        "room_name": room_info.get('name'),
                        "room_description": room_info.get('description', ''),
                        "app_url": "https://your-app.com"
                    }
                }
                await self._send_email_via_service(email_data)
            
        except Exception as e:
            logger.error(f"Error sending room invite notifications: {e}")
    
    async def _process_room_invite_notification(self, data: Dict[str, Any]) -> bool:
        """Process a room invitation notification."""
        try:
            # Extract data
            invitee_id = data.get("invitee_id")
            inviter_info = data.get("inviter_info", {})
            room_info = data.get("room_info", {})
            
            if not all([invitee_id, inviter_info, room_info]):
                logger.error("Missing required fields in room invite notification")
                return True  # Don't requeue malformed messages
            
            # Convert string ID back to UUID
            invitee_uuid = UUIDType(invitee_id)
            
            # Create notification in database
            async for session in sessionmanager.get_session():
                success = await self._create_database_notifications(
                    session, 
                    room_info.get("room_id", ""), 
                    room_info.get("room_id", ""),
                    inviter_info,
                    f"invited you to join {room_info.get('name', 'a room')}",
                    [invitee_uuid]
                )
                
                if success:
                    # Send push and email notifications
                    await self._send_room_invite_notifications(session, data)
                
                return success
                
        except Exception as e:
            logger.error(f"Error processing room invite notification: {e}")
            return False
    
    async def _process_friend_request_notification(self, data: Dict[str, Any]) -> bool:
        """Process a friend request notification."""
        try:
            # Extract data
            recipient_id = data.get("recipient_id")
            sender_info = data.get("sender_info", {})
            request_type = data.get("request_type", "friend_request")  # friend_request or friend_request_accepted
            
            if not all([recipient_id, sender_info]):
                logger.error("Missing required fields in friend request notification")
                return True  # Don't requeue malformed messages
            
            # Convert string ID back to UUID
            recipient_uuid = UUIDType(recipient_id)
            
            # Prepare content based on request type
            if request_type == "friend_request":
                content = f"{sender_info.get('display_name', sender_info.get('username'))} sent you a friend request"
            else:  # friend_request_accepted
                content = f"{sender_info.get('display_name', sender_info.get('username'))} accepted your friend request"
            
            # Create notification in database
            async for session in sessionmanager.get_session():
                success = await self._create_database_notifications(
                    session,
                    "",  # No room_id for friend requests
                    "",  # No room_id for friend requests
                    sender_info,
                    content,
                    [recipient_uuid]
                )
                
                if success:
                    # Send push and email notifications for friend requests
                    await self._send_friend_request_notifications(
                        session, recipient_uuid, sender_info, request_type
                    )
                
                return success
                
        except Exception as e:
            logger.error(f"Error processing friend request notification: {e}")
            return False
    
    async def _send_friend_request_notifications(
        self,
        session: AsyncSession,
        recipient_id: UUIDType,
        sender_info: Dict[str, Any],
        request_type: str
    ) -> None:
        """Send notifications for friend requests."""
        try:
            # Get the recipient user
            recipient = await session.get(User, recipient_id)
            if not recipient:
                logger.error(f"Recipient user not found: {recipient_id}")
                return
            
            # Prepare notification content
            if request_type == "friend_request":
                title = "Friend Request"
                body = f"{sender_info.get('display_name', sender_info.get('username'))} wants to be your friend"
                email_subject = "New Friend Request"
                email_template = "friend_request"
            else:  # friend_request_accepted
                title = "Friend Request Accepted"
                body = f"{sender_info.get('display_name', sender_info.get('username'))} accepted your friend request"
                email_subject = "Friend Request Accepted"
                email_template = "friend_request_accepted"
            
            # Send push notification
            if getattr(recipient, 'push_notifications', True) and recipient.push_token:
                push_data = {
                    "title": title,
                    "body": body,
                    "data": {
                        "type": request_type,
                        "sender_id": sender_info.get("user_id"),
                        "click_action": "FLUTTER_NOTIFICATION_CLICK"
                    },
                    "token": recipient.push_token
                }
                await self._send_fcm_notification(push_data)
            
            # Send email notification
            if getattr(recipient, 'email_notifications', True):
                email_data = {
                    "to": recipient.email,
                    "subject": email_subject,
                    "template": email_template,
                    "template_data": {
                        "recipient_name": recipient.display_name or recipient.username,
                        "sender_name": sender_info.get('display_name', sender_info.get('username')),
                        "app_url": "https://your-app.com"
                    }
                }
                await self._send_email_via_service(email_data)
            
        except Exception as e:
            logger.error(f"Error sending friend request notifications: {e}")
    
    async def _update_notification_status(
        self,
        session: AsyncSession,
        notification_ids: List[UUIDType],
        status: NotificationStatus
    ) -> None:
        """Update the status of processed notifications."""
        try:
            from realtime_messaging.services.notification_service import NotificationService
            
            for notification_id in notification_ids:
                await NotificationService.update_notification_status(
                    session, notification_id, status
                )
            
        except Exception as e:
            logger.error(f"Error updating notification status: {e}")


# Global worker instance
notification_worker = NotificationWorker()


async def start_worker():
    """Start the notification worker."""
    await notification_worker.start()


async def stop_worker():
    """Stop the notification worker."""
    await notification_worker.stop()


if __name__ == "__main__":
    """Run the worker as a standalone process."""
    try:
        logger.info("Starting notification worker...")
        asyncio.run(start_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
    finally:
        logger.info("Worker shutdown")