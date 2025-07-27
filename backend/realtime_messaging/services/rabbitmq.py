import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from uuid import UUID as UUIDType

import aio_pika
from aio_pika import connect_robust, Message, DeliveryMode
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractQueue

from realtime_messaging.config import settings


# Configure logging
logger = logging.getLogger(__name__)

# Queue names
NOTIFICATION_QUEUE = "message_notifications"
EMAIL_QUEUE = "email_notifications"
PUSH_NOTIFICATION_QUEUE = "push_notifications"

# Exchange names
NOTIFICATION_EXCHANGE = "notifications"


class RabbitMQService:
    """Service for RabbitMQ message queue operations."""
    
    def __init__(self):
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.queues: Dict[str, AbstractQueue] = {}
        self.exchange = None
        
    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            self.connection = await connect_robust(
                settings.rabbitmq_url,
                client_properties={"connection_name": "messaging-app"}
            )
            self.channel = await self.connection.channel()
            
            # Set QoS to process one message at a time
            await self.channel.set_qos(prefetch_count=1)
            
            # Create exchange
            self.exchange = await self.channel.declare_exchange(
                NOTIFICATION_EXCHANGE,
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )
            
            # Create queues
            await self._create_queues()
            
            logger.info("Successfully connected to RabbitMQ")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                
            logger.info("Disconnected from RabbitMQ")
            
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    async def _create_queues(self) -> None:
        """Create and bind queues."""
        queues_config = [
            {
                "name": NOTIFICATION_QUEUE,
                "routing_key": "notification.message.*",
                "durable": True
            },
            {
                "name": EMAIL_QUEUE,
                "routing_key": "notification.email.*",
                "durable": True
            },
            {
                "name": PUSH_NOTIFICATION_QUEUE,
                "routing_key": "notification.push.*",
                "durable": True
            }
        ]
        
        for queue_config in queues_config:
            queue = await self.channel.declare_queue(
                queue_config["name"],
                durable=queue_config["durable"]
            )
            
            await queue.bind(
                self.exchange,
                routing_key=queue_config["routing_key"]
            )
            
            self.queues[queue_config["name"]] = queue
            logger.info(f"Created queue: {queue_config['name']}")
    
    async def publish_message_notification(
        self,
        message_data: Dict[str, Any],
        routing_key: str = "notification.message.new"
    ) -> bool:
        """Publish a message notification to RabbitMQ."""
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()
            
            # Add metadata
            notification_payload = {
                **message_data,
                "timestamp": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
            
            message = Message(
                json.dumps(notification_payload, default=str).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                headers={
                    "content_type": "application/json",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            await self.exchange.publish(
                message,
                routing_key=routing_key
            )
            
            logger.info(f"Published notification: {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish notification: {e}")
            return False
    
    async def publish_email_notification(
        self,
        email_data: Dict[str, Any],
        routing_key: str = "notification.email.send"
    ) -> bool:
        """Publish an email notification to RabbitMQ."""
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()
            
            email_payload = {
                **email_data,
                "timestamp": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
            
            message = Message(
                json.dumps(email_payload, default=str).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                headers={
                    "content_type": "application/json",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            await self.exchange.publish(
                message,
                routing_key=routing_key
            )
            
            logger.info(f"Published email notification: {routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish email notification: {e}")
            return False
    
    async def consume_notifications(
        self,
        callback: Callable,
        queue_name: str = NOTIFICATION_QUEUE
    ) -> None:
        """Start consuming notifications from a queue."""
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()
            
            queue = self.queues.get(queue_name)
            if not queue:
                raise ValueError(f"Queue {queue_name} not found")
            
            async def message_handler(message: aio_pika.IncomingMessage):
                async with message.process():
                    try:
                        # Parse message
                        data = json.loads(message.body.decode())
                        
                        # Process notification
                        success = await callback(data)
                        
                        if not success:
                            # Reject and requeue with limit
                            retry_count = data.get("retry_count", 0)
                            if retry_count < 3:
                                # Increment retry count and republish
                                data["retry_count"] = retry_count + 1
                                await self.publish_message_notification(
                                    data,
                                    routing_key="notification.message.retry"
                                )
                            else:
                                logger.error(f"Max retries exceeded for notification: {data}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing notification: {e}")
            
            # Start consuming
            await queue.consume(message_handler)
            logger.info(f"Started consuming from queue: {queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to start consuming: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check RabbitMQ connection health."""
        try:
            if not self.connection or self.connection.is_closed:
                return False
            
            if not self.channel or self.channel.is_closed:
                return False
            
            return True
            
        except Exception:
            return False


# Global RabbitMQ service instance
rabbitmq_service = RabbitMQService()


async def publish_message_notification(
    message_id: UUIDType,
    room_id: UUIDType,
    sender_id: UUIDType,
    recipient_ids: list[UUIDType],
    message_content: str,
    sender_info: Dict[str, Any]
) -> bool:
    """Convenience function to publish message notifications."""
    notification_data = {
        "type": "new_message",
        "message_id": str(message_id),
        "room_id": str(room_id),
        "sender_id": str(sender_id),
        "recipient_ids": [str(uid) for uid in recipient_ids],
        "message_content": message_content,
        "sender_info": sender_info
    }
    
    return await rabbitmq_service.publish_message_notification(notification_data)


async def publish_email_notification(
    recipient_email: str,
    subject: str,
    template: str,
    template_data: Dict[str, Any]
) -> bool:
    """Convenience function to publish email notifications."""
    email_data = {
        "recipient_email": recipient_email,
        "subject": subject,
        "template": template,
        "template_data": template_data
    }
    
    return await rabbitmq_service.publish_email_notification(email_data)


# Startup and shutdown handlers
async def startup_rabbitmq():
    """Initialize RabbitMQ connection on startup."""
    try:
        await rabbitmq_service.connect()
        logger.info("RabbitMQ service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize RabbitMQ service: {e}")


async def shutdown_rabbitmq():
    """Close RabbitMQ connection on shutdown."""
    try:
        await rabbitmq_service.disconnect()
        logger.info("RabbitMQ service shut down")
    except Exception as e:
        logger.error(f"Error shutting down RabbitMQ service: {e}")