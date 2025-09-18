# Realtime Messaging App - Architecture Design

## Overview

This document outlines the architecture design of the realtime messaging application, following modern software engineering principles with clear separation of concerns, testability, and scalability.

## Architecture Pattern

The application follows a **Layered Architecture** pattern (enhanced MVC) with **Domain-Driven Design** principles:

### Core Layers

1. **Presentation Layer** (`routes/`) - HTTP request handling
2. **Service Layer** (`services/`) - Business logic and domain operations
3. **Data Layer** (`models/`) - Data structures and database entities
4. **Infrastructure Layer** (`db/`, `config/`) - Cross-cutting concerns

## Directory Structure

```
backend/
├── realtime_messaging/
│   ├── routes/           # Controllers/Presentation Layer
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── users.py      # User management endpoints
│   │   ├── rooms.py      # Room management endpoints
│   │   ├── messages.py   # Message handling endpoints
│   │   └── notifications.py # Notification endpoints
│   │
│   ├── services/         # Business Logic Layer
│   │   ├── auth.py       # Authentication business logic
│   │   ├── user_service.py # User operations
│   │   ├── room_service.py # Room management logic
│   │   ├── message_service.py # Message processing
│   │   └── notification_service.py # Notification handling
│   │
│   ├── models/           # Data Layer
│   │   ├── user.py       # User entity and validation models
│   │   ├── userprofile.py # User profile extension
│   │   ├── chat_room.py  # Room entity and validation models
│   │   ├── message.py    # Message entity and validation models
│   │   ├── notification.py # Notification models
│   │   └── room_participant.py # Participant relationship
│   │
│   ├── db/               # Database Infrastructure
│   │   └── depends.py    # Database session management
│   │
│   ├── websocket/        # Real-time Communication
│   ├── config.py         # Application configuration
│   ├── dependencies.py   # Dependency injection
│   ├── exceptions.py     # Custom exception classes
│   └── const.py          # Application constants
```

## Design Principles

### 1. **Separation of Concerns**

#### Routes (Controllers)
- **Responsibility**: Handle HTTP requests/responses only
- **Characteristics**: Thin controllers, no business logic
- **Example**:
```python
@router.post("/rooms", response_model=ChatRoomGet)
async def create_room(room_data: ChatRoomCreate, current_user: CurrentUser):
    # Delegate to service layer
    room = await RoomService.create_room(session, room_data, current_user.user_id)
    return ChatRoomGet.model_validate(room)
```

#### Services (Business Logic)
- **Responsibility**: Core business operations and domain logic
- **Characteristics**: Framework-agnostic, easily testable
- **Example**:
```python
class RoomService:
    @staticmethod
    async def create_room(session: AsyncSession, room_data: ChatRoomCreate, creator_id: UUID) -> ChatRoom:
        # Business validation
        # Database operations  
        # Cache management
        # Return domain entity
```

#### Models (Data Layer)
- **Pydantic Models**: API validation and serialization
- **SQLAlchemy Models**: Database entities and relationships
- **Shared Validation**: Common validation logic in base classes

### 2. **Data Models Architecture**

#### User System
```python
# Core User Entity
class User(Base):
    user_id: UUID (Primary Key)
    email: str (Unique)
    username: str (Unique)
    hashed_password: str
    display_name: str
    
# Extended Profile (One-to-One)
class UserProfile(Base):
    user_id: UUID (Foreign Key to User, Primary Key)
    phone_number: str
    address: str
    education: str
    # ... other profile fields
```

#### Room System
```python
# Room Entity with Privacy Control
class ChatRoom(Base):
    room_id: UUID (Primary Key)
    name: str
    description: str
    is_private: bool (Default: False)
    max_participants: int
    avatar_url: str
    settings: JSONB (Flexible configuration)
    created_at: DateTime
    updated_at: DateTime
    
# Room Participation (Many-to-Many)
class RoomParticipant(Base):
    room_id: UUID (Foreign Key)
    user_id: UUID (Foreign Key)
    joined_at: DateTime
```

### 3. **API Design Patterns**

#### Public vs Private Room Access
- **Public Rooms** (`is_private = false`):
  - Discoverable via `/rooms/public`
  - Previewable via `/rooms/{id}/preview`
  - Joinable without invitation
  
- **Private Rooms** (`is_private = true`):
  - Not discoverable
  - Invitation-only access
  - Full details only for participants

#### Pagination Strategy
```python
# Service Layer returns both data and count
async def get_public_rooms(session, pagination) -> tuple[List[PublicRoomSummary], int]:
    # Efficient count query (no joins)
    total_count = await session.execute(select(func.count(ChatRoom.room_id))...)
    
    # Paginated data query (with joins)
    rooms = await session.execute(select(...).limit().offset()...)
    
    return rooms, total_count

# Route layer sets header
response.headers["X-Total-Rooms"] = str(total_count)
```

## Testing Strategy

### Unit Testing (Services)
- **Focus**: Business logic validation
- **Characteristics**: Fast, isolated, mocked dependencies
- **Test Cases**:
  - Room creation validation
  - User authentication logic
  - Message processing rules
  - Permission checking

```python
@pytest.mark.asyncio
async def test_create_room_success():
    mock_session = AsyncMock()
    room_data = ChatRoomCreate(name="Test Room", is_private=False)
    
    result = await RoomService.create_room(mock_session, room_data, user_id)
    
    assert result.name == "Test Room"
    mock_session.add.assert_called_once()
```

### Integration Testing (Routes)
- **Focus**: HTTP API contracts and end-to-end flow
- **Characteristics**: Full stack, real database, authentication
- **Test Cases**:
  - API endpoint responses
  - Authentication flows
  - Error handling
  - Response formatting

```python
@pytest.mark.asyncio
async def test_create_room_endpoint(client: AsyncClient, auth_headers):
    response = await client.post("/rooms/", 
                               json={"name": "Test Room"}, 
                               headers=auth_headers)
    
    assert response.status_code == 201
    assert response.json()["name"] == "Test Room"
```

## Database Design

### Key Relationships

1. **User ↔ UserProfile**: One-to-One (Extended profile data)
2. **User ↔ ChatRoom**: Many-to-Many via RoomParticipant
3. **ChatRoom ↔ Message**: One-to-Many
4. **User ↔ Notification**: One-to-Many

### Performance Optimizations

- **Indexes**: On foreign keys and frequently queried fields
- **Pagination**: Efficient count queries separate from data queries
- **Caching**: Redis for frequently accessed data (room participants)
- **Database Sessions**: Proper async session management

## Security Architecture

### Authentication & Authorization
- **JWT Tokens**: Stateless authentication
- **Role-Based Access**: User permissions for room operations
- **Room Privacy**: Strict access control for private rooms

### Data Validation
- **Pydantic Models**: Input validation and serialization
- **SQLAlchemy Constraints**: Database-level integrity
- **Custom Validators**: Business rule validation

## Real-time Features

### WebSocket Architecture
- **Connection Management**: User session tracking
- **Message Broadcasting**: Room-based message distribution
- **Presence Status**: Online/offline user tracking

### Notification System
- **Async Processing**: RabbitMQ for notification queuing
- **Multi-channel**: WebSocket + Push notifications
- **Persistence**: Database storage for notification history

## Scalability Considerations

### Horizontal Scaling
- **Stateless Services**: Easy to replicate
- **Database Sharding**: User-based or room-based partitioning
- **Caching Strategy**: Redis for session and frequently accessed data

### Performance Monitoring
- **Database Query Optimization**: Avoid N+1 queries
- **Connection Pooling**: Efficient database connections
- **Resource Monitoring**: Memory and CPU usage tracking

## Configuration Management

### Environment-Based Settings
```python
class Settings:
    database_url: str
    redis_url: str
    jwt_secret_key: str
    cors_origins: List[str]
    system_timezone: str = "UTC"
```

### Feature Flags
- Room privacy settings
- Notification preferences
- Rate limiting configurations

## Deployment Architecture

### Container Strategy
- **Backend**: FastAPI application container
- **Database**: PostgreSQL with persistent volumes
- **Cache**: Redis for session management
- **Queue**: RabbitMQ for async processing

### Infrastructure
- **Kubernetes**: Container orchestration
- **Load Balancing**: Multiple application instances
- **Database Replication**: Read/write split for performance

---

## Conclusion

This architecture provides:

✅ **Maintainability**: Clear separation of concerns and layered design  
✅ **Testability**: Independent unit and integration testing strategies  
✅ **Scalability**: Stateless services and efficient data access patterns  
✅ **Security**: Comprehensive authentication and authorization  
✅ **Performance**: Optimized queries and caching strategies  
✅ **Extensibility**: Modular design for feature additions

The architecture follows modern software engineering principles and industry best practices, ensuring the application can grow and evolve while maintaining code quality and performance.