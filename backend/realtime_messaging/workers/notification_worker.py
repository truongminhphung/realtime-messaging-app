import asyncio
import json
import aio_pika
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging

from realtime_messaging.models.notification import NotificationType, NotificationStatus
from realtime_messaging.services.email_service import EmailService
from realtime_messaging.services.user_service import UserService
from realtime_messaging.websocket.notification_manager import notification_manager
from realtime_messaging.services.notification_service import NotificationService
from realtime_messaging.config import settings
from realtime_messaging.exceptions import NotFoundError
from realtime_messaging.db.depends import get_db, sessionmanager
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NotificationWorker:
    def __init__(self):
        self.rabbitmq_url = settings.rabbitmq_url
        self.email_service = EmailService()

    async def start_consuming(self):
        """Start consuming messages from RabbitMQ."""
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            "notifications", aio_pika.ExchangeType.TOPIC, durable=True
        )

        # Queue for email notifications
        email_queue = await channel.declare_queue("notification.email", durable=True)
        await email_queue.bind(exchange=exchange, routing_key="notification.*")

        # Queue for push notifications
        push_queue = await channel.declare_queue("notification.push", durable=True)
        await push_queue.bind(exchange=exchange, routing_key="notification.*")

        # start consuming messages
        await email_queue.consume(self._process_email_notification)
        await push_queue.consume(self._process_push_notification)

        logger.info("Notification worker started consuming...")

    async def _process_email_notification(self, message: aio_pika.IncomingMessage):
        """Process email notification messages."""
        async with message.process():
            session: AsyncSession = None
            try:
                payload = json.loads(message.body.decode())
                print(f"\n[DEBUG] Payload: {payload}\n")

                # Get database session
                # session = next(get_db())
                async for session in get_db():
                    user_id = payload["user_id"]
                    notification_type = payload["type"]
                    notification_id = payload.get("notification_id")

                    if notification_type == NotificationType.ROOM_INVITATION.value:
                        await self._send_room_invitation_email(session, payload)
                    elif notification_type == NotificationType.NEW_MESSAGE.value:
                        await self._send_new_message_email(session, payload)

                    # Update notification status to SENT
                    if notification_id:
                        await self._update_notification_status(
                            session, notification_id, NotificationStatus.SENT
                        )

                        # Send real-time notification via WebSocket
                        await self._send_websocket_notification(payload)

                    logger.info(
                        f"Email notification {notification_id} sent successfully to user {user_id}"
                    )
                    break  # Exit after using one session

            except Exception as e:
                logger.error(f"Failed to process email notification: {e}")
                # Update notification status to FAILED if we have notification_id
                if session and payload.get("notification_id"):
                    try:
                        await self._update_notification_status(
                            session,
                            payload["notification_id"],
                            NotificationStatus.FAILED,
                        )
                    except Exception as update_error:
                        logger.error(
                            f"Failed to update notification status: {update_error}"
                        )
                # Message will be requeued for retry
                raise
            finally:
                if session:
                    await session.close()

    async def _send_room_invitation_email(self, session: AsyncSession, payload: dict):
        """Send room invitation email."""
        user_id = payload["user_id"]
        room_name = payload["data"]["room_name"]

        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        # Construct email
        subject = f"You've been invited to join '{room_name}'"
        body = f"""
        Hello {user.display_name or user.username},
        
        You've been invited to join the room '{room_name}' in our messaging app.

        Click here to join: {settings.frontend_url}/rooms/{payload['data']['room_id']}/join

        Best regards,
        The Messaging Team
        """

        # Send email
        await self.email_service.send_email(
            to_email=user.email, subject=subject, body=body
        )

    async def _send_new_message_email(self, session: AsyncSession, payload: dict):
        """Send new message email notification."""
        user_id = payload["user_id"]
        room_name = payload["data"]["room_name"]
        sender_name = payload["data"]["sender_name"]
        message_snippet = payload["data"]["message_snippet"]

        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        # Construct email
        subject = f"New message in '{room_name}' from {sender_name}"
        body = f"""
        Hello {user.display_name or user.username},
        
        You have a new message in the room '{room_name}' from {sender_name}:

        "{message_snippet}..."

        Click here to view the message: {settings.frontend_url}/rooms/{payload['data']['room_id']}

        Best regards,
        The Messaging Team
        """

        # Send email
        await self.email_service.send_email(to=user.email, subject=subject, body=body)

    async def _process_push_notification(self, message: aio_pika.IncomingMessage):
        """Process push notification messages."""
        async with message.process():
            try:
                payload = json.loads(message.body.decode())
                user_id = payload["user_id"]
                notification_type = payload["type"]

                logger.info(
                    f"Processing push notification for user {user_id}, type: {notification_type}"
                )

                # TODO: Implement push notification logic (FCM, APNs, etc.)
                # For now, just log it
                logger.info("Push notification processed (implementation pending)")

            except Exception as e:
                logger.error(f"Failed to process push notification: {e}")
                raise

    async def _update_notification_status(
        self, session: AsyncSession, notification_id: str, status: NotificationStatus
    ):
        """Update notification status in database."""
        try:
            await NotificationService.update_notification_status(
                session, notification_id, status
            )
            await session.commit()
            logger.info(
                f"Updated notification {notification_id} status to {status.value}"
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update notification status: {e}")
            raise

    async def _send_websocket_notification(self, payload: dict):
        """Send real-time notification via WebSocket."""
        try:
            user_id = payload.get("user_id")
            if not user_id:
                logger.warning("No user_id in payload for WebSocket notification")
                return

            # Format notification data for WebSocket
            websocket_data = {
                "type": payload.get("type", "unknown"),
                "title": self._get_notification_title(payload),
                "message": self._get_notification_message(payload),
                "data": payload.get("data", {}),
                "timestamp": payload.get("timestamp", ""),
            }

            # Send to notification manager
            await notification_manager.send_notification_to_user(
                user_id, websocket_data
            )
            logger.info(f"WebSocket notification sent to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")
            # Don't raise - WebSocket failures shouldn't block email notifications

    def _get_notification_title(self, payload: dict) -> str:
        """Get notification title based on type."""
        notification_type = payload.get("type", "")

        if notification_type == "room_invitation":
            room_name = payload.get("data", {}).get("room_name", "a room")
            return f"Invitation to join '{room_name}'"
        elif notification_type == "new_message":
            room_name = payload.get("data", {}).get("room_name", "a room")
            sender_name = payload.get("data", {}).get("sender_name", "Someone")
            return f"New message from {sender_name} in '{room_name}'"
        else:
            return "New notification"

    def _get_notification_message(self, payload: dict) -> str:
        """Get notification message based on type."""
        notification_type = payload.get("type", "")

        if notification_type == "room_invitation":
            inviter_name = payload.get("data", {}).get("inviter_name", "Someone")
            room_name = payload.get("data", {}).get("room_name", "a room")
            return f"{inviter_name} invited you to join '{room_name}'"
        elif notification_type == "new_message":
            sender_name = payload.get("data", {}).get("sender_name", "Someone")
            message_snippet = payload.get("data", {}).get("message_snippet", "")
            return f"{sender_name}: {message_snippet}..."
        else:
            return "You have a new notification"


# Worker entry point
async def main():
    """Main entry point for the notification worker."""
    # Initialize database session manager
    logger.info("Initializing database session manager...")
    sessionmanager.init_db()

    worker = NotificationWorker()
    try:
        await worker.start_consuming()
        # Keep the worker running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Notification worker stopped by user")
    except Exception as e:
        logger.error(f"Notification worker crashed: {e}")
        raise
    finally:
        # Clean up database connections
        logger.info("Closing database connections...")
        await sessionmanager.close()


if __name__ == "__main__":
    asyncio.run(main())
