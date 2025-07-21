# Database Connection and User Operations

This document explains how to use the async database connection and user operations that have been implemented following FastAPI and SQLAlchemy best practices.

## Database Connection Architecture

The database connection is managed using a `SessionManager` class that provides:

- **Connection Pooling**: Using `AsyncAdaptedQueuePool` for efficient connection management
- **Async Support**: Full async/await support with `asyncpg` driver
- **Dependency Injection**: Clean integration with FastAPI's dependency system
- **Error Handling**: Proper session rollback and error management

### Key Components

1. **SessionManager** (`app/db/depends.py`): Manages database engine and session factory
2. **UserService** (`app/services/user_service.py`): Handles all user CRUD operations
3. **Dependencies** (`app/dependencies.py`): FastAPI dependency providers
4. **User Routes** (`app/routes/users.py`): REST API endpoints for user operations

## Usage Examples

### 1. Using Database Session in FastAPI Routes

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.depends import get_db

@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db)
):
    user = await UserService.get_user_by_id(session, user_id)
    return user
```

### 2. Using Database Session in Scripts

```python
import asyncio
from app.db.depends import sessionmanager

async def my_script():
    sessionmanager.init_db()
    
    async for session in sessionmanager.get_session():
        # Your database operations here
        user = await UserService.get_user_by_email(session, "user@example.com")
        break
    
    await sessionmanager.close()

asyncio.run(my_script())
```

### 3. User Operations

The `UserService` class provides these methods:

- `create_user(session, user_data)`: Create a new user
- `get_user_by_id(session, user_id)`: Get user by ID
- `get_user_by_email(session, email)`: Get user by email
- `get_user_by_username(session, username)`: Get user by username
- `update_user(session, user_id, user_data)`: Update user information
- `delete_user(session, user_id)`: Delete a user
- `authenticate_user(session, email, password)`: Authenticate user with email/password

## Available API Endpoints

### User Management

- `POST /users/` - Create a new user
- `GET /users/{user_id}` - Get user by ID
- `GET /users/email/{email}` - Get user by email
- `GET /users/username/{username}` - Get user by username
- `PUT /users/{user_id}` - Update user information
- `DELETE /users/{user_id}` - Delete a user

### Request/Response Examples

#### Create User
```json
POST /users/
{
    "email": "john.doe@example.com",
    "username": "johndoe",
    "password": "securepassword123",
    "display_name": "John Doe",
    "profile_picture_url": "https://example.com/avatar.jpg"
}
```

#### Response
```json
{
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "john.doe@example.com",
    "username": "johndoe",
    "display_name": "John Doe",
    "profile_picture_url": "https://example.com/avatar.jpg",
    "created_at": "2025-01-21T10:30:00Z",
    "updated_at": "2025-01-21T10:30:00Z"
}
```

## Configuration

The database connection is configured through environment variables:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/messaging_app
DEBUG=true
```

The system automatically converts PostgreSQL URLs to async format (`postgresql+asyncpg://`).

## Security Features

- **Password Hashing**: Uses bcrypt for secure password storage
- **Input Validation**: Pydantic models ensure data integrity
- **SQL Injection Protection**: SQLAlchemy ORM provides safe query building
- **Connection Security**: Pool pre-ping ensures connection health

## Error Handling

The system provides proper error handling for:

- Duplicate emails/usernames
- User not found scenarios
- Database connection issues
- Authentication failures

## Testing

Run the example script to test the implementation:

```bash
cd backend
python example_user_operations.py
```

This will demonstrate:
- Creating a user
- Retrieving users by different fields
- User authentication
- Error handling for duplicate entries

## Dependencies

Make sure you have these packages installed:

- `fastapi`
- `sqlalchemy[asyncio]`
- `asyncpg`
- `passlib[bcrypt]`
- `pydantic[email]`

The complete list is in `pyproject.toml`.
