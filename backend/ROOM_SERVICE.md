# Room Service Documentation

This document describes the Room Service implementation that provides comprehensive room management functionality for the messaging application.

## Overview

The Room Service builds on the authentication and user services to enable:
- Room creation and management
- User participation in rooms
- Room invitations and notifications
- Participant management with Redis caching
- Comprehensive access control

## Architecture

### Dependencies
- **Authentication Service**: JWT-based user authentication
- **User Service**: User management and validation
- **Database**: PostgreSQL with async SQLAlchemy
- **Caching**: Redis for participant list caching
- **Notifications**: Room invitation notifications

### Database Tables
- `chat_rooms`: Room information (ID, name, creator, timestamps)
- `room_participants`: Many-to-many relationship between users and rooms
- `users`: User information for participants
- `notifications`: Room invitation notifications

## API Endpoints

### 1. Room CRUD Operations

#### Create Room
```http
POST /rooms
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "name": "My Chat Room"
}
```

**Response**:
```json
{
    "room_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "My Chat Room",
    "creator_id": "987fcdeb-51a2-43d1-9f4e-6789abcdef00",
    "created_at": "2025-01-26T10:30:00Z"
}
```

#### Get User's Rooms
```http
GET /rooms
Authorization: Bearer <jwt_token>
```

**Response**:
```json
[
    {
        "room_id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "My Chat Room",
        "creator_id": "987fcdeb-51a2-43d1-9f4e-6789abcdef00",
        "created_at": "2025-01-26T10:30:00Z"
    }
]
```

#### Get Room Details
```http
GET /rooms/{room_id}
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
    "room_id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "My Chat Room",
    "creator_id": "987fcdeb-51a2-43d1-9f4e-6789abcdef00",
    "created_at": "2025-01-26T10:30:00Z",
    "participant_count": 5
}
```

#### Update Room
```http
PUT /rooms/{room_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "name": "Updated Room Name"
}
```

#### Delete Room
```http
DELETE /rooms/{room_id}
Authorization: Bearer <jwt_token>
```

### 2. Room Participation

#### Invite User to Room
```http
POST /rooms/{room_id}/invite
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "email": "user@example.com"
}
```

**Response**:
```json
{
    "message": "Invitation sent to user@example.com",
    "room_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### Join Room
```http
POST /rooms/{room_id}/join
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
    "message": "Successfully joined the room",
    "room_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### Leave Room
```http
POST /rooms/{room_id}/leave
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
    "message": "Successfully left the room"
}
```

#### Get Room Participants
```http
GET /rooms/{room_id}/participants
Authorization: Bearer <jwt_token>
```

**Response**:
```json
[
    {
        "user_id": "987fcdeb-51a2-43d1-9f4e-6789abcdef00",
        "username": "johndoe",
        "display_name": "John Doe",
        "profile_picture_url": "https://example.com/avatar.jpg",
        "joined_at": "2025-01-26T10:30:00Z"
    }
]
```

## Service Implementation

### RoomService Class Methods

#### Core Room Operations
- `create_room()`: Creates room and adds creator as first participant
- `get_room()`: Retrieves room by ID
- `get_user_rooms()`: Gets all rooms for a user
- `update_room()`: Updates room details (creator only)
- `delete_room()`: Deletes room (creator only)

#### Participation Management
- `join_room()`: Adds user to room participants
- `leave_room()`: Removes user from room participants
- `is_user_participant()`: Checks if user is room participant
- `get_room_participants()`: Gets participant list with caching

#### Invitation System
- `invite_user_to_room()`: Sends invitation and creates notification
- `get_room_with_participant_count()`: Gets room with participant count

### Key Features

#### 1. Access Control
- **Authentication Required**: All endpoints require valid JWT
- **Participant-Only Access**: Room details/participants only accessible to members
- **Creator Privileges**: Only room creators can update/delete rooms
- **Invitation Rights**: Any participant can invite others

#### 2. Performance Optimization
- **Redis Caching**: Participant lists cached for 5 minutes
- **Async Operations**: Full async/await support
- **Connection Pooling**: Efficient database connections
- **Single Queries**: Optimized database operations

#### 3. Data Integrity
- **Unique Constraints**: Prevents duplicate room participants
- **Cascade Deletes**: Room deletion removes all participants
- **Transaction Safety**: Proper rollback on errors
- **Input Validation**: Comprehensive data validation

#### 4. Notification Integration
- **Room Invitations**: Creates notifications for invites
- **JSON Content**: Structured notification data
- **Future RabbitMQ**: Ready for async notification processing

## Validation Rules

### Room Creation
- Room name is required and cannot be empty
- Room name maximum 100 characters
- Creator automatically becomes first participant

### Room Updates
- Only room creator can update room details
- Room name validation same as creation
- Partial updates supported

### Room Deletion
- Only room creator can delete rooms
- All participants automatically removed
- Cached data cleared

### Participation
- Users cannot join rooms multiple times (handled gracefully)
- Users must be participants to view room details
- Users can only leave rooms they're already in

### Invitations
- Can only invite existing users (by email)
- Cannot invite users who are already participants
- Only participants can send invitations
- Creates notification for invited user

## Error Handling

### 400 Bad Request
- Empty or invalid room names
- Attempting to invite non-existent users
- Attempting to invite existing participants
- Invalid email formats

### 403 Forbidden
- Non-participants trying to access room details
- Non-creators trying to update/delete rooms
- Non-participants trying to invite others

### 404 Not Found
- Room not found
- User not found for invitations

### 500 Internal Server Error
- Database connection issues
- Redis connection problems
- Unexpected server errors

## Performance Characteristics

### Database Optimization
- **Indexes**: room_id, user_id, creator_id are indexed
- **Query Optimization**: Single queries for operations
- **Connection Pooling**: Async connection management

### Caching Strategy
- **Participant Lists**: Cached in Redis for 5 minutes
- **Cache Invalidation**: Cleared on participant changes
- **Fallback**: Graceful fallback to database on cache miss

### Scalability Features
- **Async Architecture**: Supports high concurrency
- **Redis Integration**: Reduces database load
- **Efficient Queries**: Optimized for 10,000+ concurrent users
- **Stateless Design**: No server-side session state

## Security Considerations

1. **JWT Authentication**: Required for all operations
2. **User Isolation**: Users can only access their permitted rooms
3. **Input Sanitization**: All inputs validated and cleaned
4. **SQL Injection Protection**: SQLAlchemy ORM parameterized queries
5. **Access Control**: Fine-grained permissions for different operations

## Integration with Other Services

### Message Service (Next)
```python
# Room validation for message sending
@router.post("/messages")
async def send_message(
    message_data: MessageCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db)
):
    # Validate user is participant in room
    is_participant = await RoomService.is_user_participant(
        session, message_data.room_id, current_user.user_id
    )
    if not is_participant:
        raise HTTPException(403, "Not a room participant")
```

### Notification Service
```python
# Room invitation notifications already integrated
# Future: RabbitMQ publishing for async processing
```

### WebSocket Service
```python
# Room-based message broadcasting
@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: UUID):
    # Validate user is participant before allowing connection
    is_participant = await RoomService.is_user_participant(
        session, room_id, user_id
    )
```

## Testing

Run the comprehensive test script:

```bash
cd backend
python test_room_service.py
```

The test covers:
- Room creation and management
- User participation workflows
- Invitation system
- Access control validation
- Error handling scenarios
- Redis caching functionality
- JWT token integration

## Why Room Service After User Profile Service

1. **Authentication Foundation**: Requires JWT tokens from auth service
2. **User Dependencies**: Needs user profiles for participants and creators
3. **Core Chat Feature**: Essential for group messaging functionality
4. **Notification Integration**: Sets up invitation notifications
5. **Message Service Prep**: Provides room validation for messaging
6. **Logical Progression**: Natural next step in chat app development

## Next Implementation Steps

After the Room Service, implement:
1. **Message Service**: Send/receive messages in rooms
2. **Notification Service**: Process room invitations and message notifications
3. **WebSocket Service**: Real-time message delivery
4. **Advanced Features**: File sharing, message reactions, etc.

The Room Service provides the essential foundation for all group communication features in the messaging application.
