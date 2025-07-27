# Notification Service Documentation

## Overview

The Notification Service is a comprehensive, high-performance notification system designed to handle 10,000+ concurrent users and 1,000+ messages per second with sub-100ms latency. It provides real-time notifications through multiple channels including push notifications, email, and WebSocket connections.

## Architecture

### Core Components

1. **Notification API (`app/routes/notifications.py`)**
   - RESTful endpoints for notification management
   - Filtering, pagination, and search capabilities
   - User preference management

2. **Notification Service (`app/services/notification_service.py`)**
   - Business logic layer with Redis caching
   - CRUD operations for notifications
   - Performance optimizations

3. **Notification Worker (`app/services/notification_worker.py`)**
   - RabbitMQ message consumer
   - FCM push notification sending
   - Email notification dispatch
   - Retry logic and error handling

4. **Integration Layer (`app/services/notification_integration.py`)**
   - Integration functions for other services
   - Fallback mechanisms for reliability
   - Notification creation helpers

5. **Database Model (`app/models/notification.py`)**
   - SQLAlchemy models with optimized indexing
   - Enum types for notification categories
   - JSON content storage

### Technology Stack

- **Database**: PostgreSQL with optimized indexing
- **Cache**: Redis with 5-minute notification cache, 1-minute count cache
- **Message Queue**: RabbitMQ for async processing
- **Push Notifications**: Firebase Cloud Messaging (FCM)
- **Email**: Simulated email service (ready for SMTP integration)
- **Framework**: FastAPI with async/await patterns

## API Endpoints

### Notification Management

#### Get User Notifications
```http
GET /api/v1/notifications
```

**Query Parameters:**
- `limit` (int, default=20): Number of notifications per page
- `offset` (int, default=0): Pagination offset
- `unread_only` (bool, default=false): Filter unread notifications only
- `notification_type` (str, optional): Filter by notification type
  - `new_message`
  - `room_invitation`
  - `friend_request`
  - `friend_request_accepted`

**Response:**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "notification_type": "new_message",
      "content": {
        "message_id": "uuid",
        "sender_username": "john_doe",
        "message_preview": "Hello, how are you?"
      },
      "status": "pending",
      "is_read": false,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 150,
  "has_more": true
}
```

#### Get Notification Count
```http
GET /api/v1/notifications/count
```

**Query Parameters:**
- `unread_only` (bool, default=false): Count unread notifications only
- `notification_type` (str, optional): Filter by notification type

**Response:**
```json
{
  "count": 25
}
```

#### Mark Notification as Read
```http
PUT /api/v1/notifications/{notification_id}/read
```

**Response:**
```json
{
  "success": true,
  "message": "Notification marked as read"
}
```

#### Mark All Notifications as Read
```http
PUT /api/v1/notifications/read-all
```

**Query Parameters:**
- `notification_type` (str, optional): Mark specific type as read

**Response:**
```json
{
  "success": true,
  "updated_count": 15,
  "message": "All notifications marked as read"
}
```

#### Delete Notification
```http
DELETE /api/v1/notifications/{notification_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Notification deleted successfully"
}
```

### Notification Preferences

#### Get User Preferences
```http
GET /api/v1/notifications/preferences
```

**Response:**
```json
{
  "push_notifications": true,
  "email_notifications": false,
  "notification_types": {
    "new_message": true,
    "room_invitation": true,
    "friend_request": false
  },
  "quiet_hours": {
    "enabled": true,
    "start_time": "22:00",
    "end_time": "08:00",
    "timezone": "UTC"
  }
}
```

#### Update User Preferences
```http
PUT /api/v1/notifications/preferences
```

**Request Body:**
```json
{
  "push_notifications": true,
  "email_notifications": false,
  "notification_types": {
    "new_message": true,
    "room_invitation": true,
    "friend_request": false
  },
  "quiet_hours": {
    "enabled": true,
    "start_time": "22:00",
    "end_time": "08:00",
    "timezone": "UTC"
  }
}
```

## Integration Guide

### For Message Service

```python
from app.services.notification_integration import create_message_notification

# When a new message is created
async def create_message(session, message_data):
    # ... create message logic ...
    
    # Send notifications to all room participants except sender
    await create_message_notification(
        session=session,
        message_id=message.id,
        room_id=message.room_id,
        sender_id=message.sender_id,
        recipient_ids=recipient_user_ids,
        message_content=message.content,
        sender_info={
            "user_id": str(sender.id),
            "username": sender.username,
            "display_name": sender.display_name
        }
    )
```

### For Room Service

```python
from app.services.notification_integration import create_room_invite_notification

# When inviting users to a room
async def invite_user_to_room(session, room_id, inviter_id, invitee_id):
    # ... invitation logic ...
    
    await create_room_invite_notification(
        session=session,
        room_id=room.id,
        room_name=room.name,
        room_description=room.description,
        inviter_id=inviter_id,
        invitee_id=invitee_id,
        inviter_info={
            "user_id": str(inviter.id),
            "username": inviter.username,
            "display_name": inviter.display_name
        }
    )
```

### For Friend Service

```python
from app.services.notification_integration import create_friend_request_notification

# When sending a friend request
async def send_friend_request(session, sender_id, recipient_id):
    # ... friend request logic ...
    
    await create_friend_request_notification(
        session=session,
        sender_id=sender_id,
        recipient_id=recipient_id,
        sender_info={
            "user_id": str(sender.id),
            "username": sender.username,
            "display_name": sender.display_name
        },
        request_type="friend_request"
    )
```

## Performance Optimizations

### Caching Strategy

1. **Notification Cache**: 5-minute TTL for user notifications
2. **Count Cache**: 1-minute TTL for notification counts
3. **Preference Cache**: 15-minute TTL for user preferences

### Database Optimizations

1. **Indexes**:
   - `(user_id, created_at)` for efficient user queries
   - `(user_id, is_read)` for unread filtering
   - `(user_id, notification_type)` for type filtering

2. **Query Optimization**:
   - Efficient pagination with offset/limit
   - Selective field loading
   - Optimized COUNT queries

### Async Processing

1. **RabbitMQ Integration**:
   - Non-blocking notification creation
   - Retry logic with exponential backoff
   - Dead letter queue for failed notifications

2. **Worker Scalability**:
   - Multiple worker instances
   - Load balancing across workers
   - Graceful shutdown handling

## Monitoring and Health Checks

### Health Check Endpoint

```http
GET /api/v1/notifications/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "rabbitmq": {"status": "healthy"}
  }
}
```

### Performance Metrics

- **Latency**: Average notification creation < 50ms
- **Throughput**: 1,000+ notifications/second
- **Cache Hit Rate**: > 80% for notification queries
- **Worker Processing**: < 100ms per notification

### Testing

Run comprehensive tests:

```bash
# From the backend directory
python -m app.utils.notification_test_utils
```

Test categories:
- Basic CRUD operations
- Integration with other services
- Performance under load
- Caching behavior
- Error handling and fallbacks

## Deployment Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300  # 5 minutes

# RabbitMQ Configuration
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_EXCHANGE=notifications
RABBITMQ_QUEUE=notification_queue

# FCM Configuration
FCM_PROJECT_ID=your-project-id
FCM_PRIVATE_KEY_ID=your-private-key-id
FCM_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FCM_CLIENT_EMAIL=firebase-service-account@your-project.iam.gserviceaccount.com
FCM_CLIENT_ID=your-client-id
FCM_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FCM_TOKEN_URI=https://oauth2.googleapis.com/token

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourapp.com
```

### Docker Configuration

The notification worker runs as a separate container:

```yaml
# docker-compose.yml
services:
  notification-worker:
    build:
      context: ./worker
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/realtime_messaging
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - rabbitmq
      - redis
    restart: unless-stopped
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notification-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: notification-worker
  template:
    metadata:
      labels:
        app: notification-worker
    spec:
      containers:
      - name: notification-worker
        image: your-registry/notification-worker:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: RABBITMQ_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: rabbitmq-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Security Considerations

1. **Authentication**: All endpoints require valid JWT tokens
2. **Authorization**: Users can only access their own notifications
3. **Input Validation**: All inputs validated using Pydantic models
4. **Rate Limiting**: API endpoints protected against abuse
5. **Data Privacy**: Notification content encrypted in transit and at rest

## Error Handling

### Common Error Responses

```json
{
  "detail": "Notification not found",
  "status_code": 404
}
```

```json
{
  "detail": "Invalid notification type",
  "status_code": 400
}
```

### Fallback Mechanisms

1. **RabbitMQ Failure**: Direct database insertion
2. **Redis Failure**: Direct database queries
3. **FCM Failure**: Retry with exponential backoff
4. **Database Failure**: Graceful degradation

## Future Enhancements

1. **Advanced Filtering**: Date ranges, content search
2. **Notification Templates**: Customizable notification formats
3. **A/B Testing**: Different notification strategies
4. **Analytics**: Notification delivery and engagement metrics
5. **Multi-tenancy**: Support for multiple organizations
6. **Real-time Updates**: WebSocket notifications for instant updates

## Support and Troubleshooting

### Common Issues

1. **High Latency**: Check Redis connection and database indexes
2. **Missing Notifications**: Verify RabbitMQ worker status
3. **Cache Issues**: Clear Redis cache and monitor hit rates
4. **Database Locks**: Monitor long-running queries

### Logs and Debugging

```bash
# View notification worker logs
docker logs notification-worker -f

# Check RabbitMQ queue status
docker exec rabbitmq rabbitmqctl list_queues

# Monitor Redis cache
docker exec redis redis-cli monitor
```

For additional support, check the project's issue tracker or contact the development team.
