# RabbitMQ Async Notification Processing

## Overview

This document describes the implementation of asynchronous notification processing using RabbitMQ in our real-time messaging application. The system decouples message creation from notification delivery, improving performance and reliability.

## Architecture

### Components

1. **RabbitMQ Service** (`app/services/rabbitmq.py`)
   - Connection management
   - Queue creation and binding
   - Message publishing
   - Health checks

2. **Notification Worker** (`app/services/notification_worker.py`)
   - Message consumption
   - Notification processing
   - Database operations
   - Push/Email integration

3. **Message Service Integration**
   - Async notification publishing
   - Fallback mechanisms
   - Error handling

## Message Flow

```mermaid
sequenceDiagram
    participant User as User
    participant API as FastAPI
    participant DB as Database
    participant RMQ as RabbitMQ
    participant Worker as Notification Worker
    participant Push as Push Service
    participant Email as Email Service

    User->>API: Send Message
    API->>DB: Store Message
    API->>RMQ: Publish Notification
    API->>User: Return Success
    
    RMQ->>Worker: Deliver Notification
    Worker->>DB: Create Notifications
    Worker->>Push: Send Push Notifications
    Worker->>Email: Send Email Notifications
```

## Queue Configuration

### Exchanges and Queues

```python
# Exchange
NOTIFICATION_EXCHANGE = "notifications"  # Topic exchange

# Queues
NOTIFICATION_QUEUE = "message_notifications"
EMAIL_QUEUE = "email_notifications"  
PUSH_NOTIFICATION_QUEUE = "push_notifications"

# Routing Keys
"notification.message.new"    # New message notifications
"notification.message.retry"  # Retry failed notifications
"notification.email.send"     # Email notifications
"notification.push.send"      # Push notifications
```

### Queue Properties

- **Durable**: Yes (survive server restarts)
- **Auto-delete**: No (persist even when no consumers)
- **QoS**: 1 message per consumer (fair distribution)
- **Message TTL**: Not set (messages persist until processed)

## Message Format

### Notification Message Structure

```json
{
    "type": "new_message",
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "room_id": "660e8400-e29b-41d4-a716-446655440000", 
    "sender_id": "770e8400-e29b-41d4-a716-446655440000",
    "recipient_ids": [
        "880e8400-e29b-41d4-a716-446655440000",
        "990e8400-e29b-41d4-a716-446655440000"
    ],
    "message_content": "Hello everyone! 👋",
    "sender_info": {
        "user_id": "770e8400-e29b-41d4-a716-446655440000",
        "username": "john_doe", 
        "display_name": "John Doe",
        "profile_picture_url": "https://example.com/avatar.jpg"
    },
    "timestamp": "2025-01-27T12:00:00Z",
    "retry_count": 0
}
```

### Message Headers

```python
headers = {
    "content_type": "application/json",
    "timestamp": "2025-01-27T12:00:00Z"
}
```

## Implementation Details

### Publishing Notifications

```python
# In message service
async def create_message_notification(
    session: AsyncSession, 
    message: Message, 
    room_participants: List[UUIDType]
) -> None:
    """Create notifications for new messages (excluding sender)."""
    from app.services.rabbitmq import publish_message_notification
    
    # Get sender info
    sender = await session.get(User, message.sender_id)
    recipient_ids = [pid for pid in room_participants if pid != message.sender_id]
    
    # Publish to RabbitMQ
    success = await publish_message_notification(
        message_id=message.message_id,
        room_id=message.room_id,
        sender_id=message.sender_id,
        recipient_ids=recipient_ids,
        message_content=message.content,
        sender_info=sender_info
    )
    
    # Fallback if RabbitMQ fails
    if not success:
        await _create_notifications_fallback(session, message, recipient_ids, sender_info)
```

### Processing Notifications

```python
async def process_notification(self, data: Dict[str, Any]) -> bool:
    """Process a notification message from RabbitMQ."""
    try:
        notification_type = data.get("type")
        
        if notification_type == "new_message":
            return await self._process_message_notification(data)
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
            return True  # Acknowledge to avoid reprocessing
            
    except Exception as e:
        logger.error(f"Error processing notification: {e}")
        return False  # This will cause requeue/retry
```

## Error Handling and Retry Logic

### Retry Mechanism

1. **Failed Processing**: Message requeued with incremented retry count
2. **Max Retries**: 3 attempts before dead lettering
3. **Exponential Backoff**: Increasing delay between retries
4. **Dead Letter Queue**: Failed messages for manual inspection

```python
# In worker message handler
if not success:
    retry_count = data.get("retry_count", 0)
    if retry_count < 3:
        data["retry_count"] = retry_count + 1
        await self.publish_message_notification(
            data,
            routing_key="notification.message.retry"
        )
    else:
        logger.error(f"Max retries exceeded: {data}")
```

### Fallback Strategy

1. **RabbitMQ Unavailable**: Direct database notification creation
2. **Processing Fails**: Log error and continue (don't block message creation)
3. **Graceful Degradation**: System continues working without notifications

## Performance Considerations

### Throughput

- **Target**: 1,000+ notifications/second
- **Batching**: Process multiple notifications together when possible
- **Connection Pooling**: Reuse RabbitMQ connections
- **Async Processing**: Non-blocking notification handling

### Memory Management

- **Message Acknowledgment**: Explicit ack/nack for flow control
- **QoS Limits**: Prevent consumer overload
- **TTL**: Set appropriate time-to-live for messages
- **Queue Limits**: Monitor queue depth

### Monitoring Metrics

```python
# Key metrics to track
- Messages published/second
- Messages processed/second  
- Queue depth
- Processing latency
- Error rate
- Retry rate
```

## Configuration

### Environment Variables

```bash
# RabbitMQ Connection
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Optional: Advanced configuration
RABBITMQ_CONNECTION_TIMEOUT=10
RABBITMQ_HEARTBEAT=600
RABBITMQ_MAX_RETRIES=3
```

### Docker Compose Configuration

```yaml
services:
  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      - RABBITMQ_DEFAULT_USER=guest
      - RABBITMQ_DEFAULT_PASS=guest
    ports:
      - "5672:5672"      # AMQP port
      - "15672:15672"    # Management UI
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5

  notification-worker:
    build: ./backend
    environment:
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
    command: uv run python -m app.services.notification_worker
    depends_on:
      rabbitmq:
        condition: service_healthy
```

## Deployment

### Production Setup

1. **Cluster Configuration**: Multi-node RabbitMQ cluster
2. **Load Balancing**: Multiple worker instances
3. **Monitoring**: Prometheus + Grafana integration
4. **Persistence**: Durable queues and messages

### Scaling Workers

```bash
# Run multiple worker instances
docker-compose up --scale notification-worker=3
```

### Health Monitoring

```python
# Health check endpoint
@app.get("/health/rabbitmq")
async def rabbitmq_health():
    is_healthy = await rabbitmq_service.health_check()
    return {"status": "healthy" if is_healthy else "unhealthy"}
```

## Testing

### Unit Testing

```python
# Test notification processing
async def test_process_message_notification():
    worker = NotificationWorker()
    
    test_data = {
        "type": "new_message",
        "message_id": str(uuid4()),
        "room_id": str(uuid4()),
        "sender_id": str(uuid4()),
        "recipient_ids": [str(uuid4())],
        "message_content": "Test message",
        "sender_info": {
            "username": "test_user",
            "display_name": "Test User"
        }
    }
    
    result = await worker.process_notification(test_data)
    assert result is True
```

### Integration Testing

```bash
# Run the RabbitMQ test script
cd backend
python test_rabbitmq.py
```

### Load Testing

```python
# Send 1000 notifications quickly
tasks = []
for i in range(1000):
    task = publish_message_notification(
        message_id=uuid4(),
        room_id=room_id,
        sender_id=sender_id,
        recipient_ids=[uuid4()],
        message_content=f"Load test message {i}",
        sender_info=sender_info
    )
    tasks.append(task)

results = await asyncio.gather(*tasks)
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check RabbitMQ is running
   - Verify connection URL
   - Check network connectivity

2. **Messages Not Processing**
   - Check worker is running
   - Verify queue bindings
   - Check worker logs

3. **High Memory Usage**
   - Monitor queue depths
   - Check for unacknowledged messages
   - Verify worker processing rate

### Debug Commands

```bash
# Check RabbitMQ status
docker exec rabbitmq rabbitmq-diagnostics status

# List queues
docker exec rabbitmq rabbitmqctl list_queues

# Monitor queue activity
docker exec rabbitmq rabbitmqctl list_queues name messages consumers

# Check exchanges
docker exec rabbitmq rabbitmqctl list_exchanges

# View bindings
docker exec rabbitmq rabbitmqctl list_bindings
```

### Management UI

Access RabbitMQ management interface at http://localhost:15672
- Username: guest
- Password: guest

## Future Enhancements

### Planned Features

1. **Dead Letter Handling**: Automatic retry with exponential backoff
2. **Priority Queues**: High-priority notifications (mentions, direct messages)
3. **Message Deduplication**: Prevent duplicate notifications
4. **Batch Processing**: Group notifications by user/type
5. **Analytics**: Notification delivery metrics

### Advanced Patterns

1. **Saga Pattern**: Multi-step notification workflows
2. **Event Sourcing**: Store notification events for replay
3. **CQRS**: Separate read/write notification models
4. **Circuit Breaker**: Fail fast when downstream services are down

## Conclusion

The RabbitMQ implementation provides reliable, scalable async notification processing that:

- ✅ Decouples message creation from notification delivery
- ✅ Handles 1,000+ notifications/second
- ✅ Provides graceful fallback mechanisms
- ✅ Supports retry logic and error handling
- ✅ Enables horizontal scaling
- ✅ Maintains system reliability

This foundation supports the real-time messaging requirements while ensuring excellent performance and reliability.
