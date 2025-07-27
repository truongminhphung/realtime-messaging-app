# User Profile Service Documentation

This document describes the User Profile Service implementation that provides endpoints for users to view and update their profile information.

## Overview

The User Profile Service builds on the authentication system to allow authenticated users to:
- View their complete profile information
- Update their display name, username, and profile picture
- Perform partial updates using PATCH operations

## API Endpoints

### 1. GET /users/profile

**Purpose**: Retrieve the current user's profile information.

**Authentication**: Required (JWT Bearer token)

**Request**:
```http
GET /users/profile
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "username": "johndoe",
    "display_name": "John Doe",
    "profile_picture_url": "https://example.com/avatar.jpg",
    "created_at": "2025-01-21T10:30:00Z",
    "updated_at": "2025-01-21T15:45:00Z"
}
```

### 2. PATCH /users/profile

**Purpose**: Update the current user's profile information (partial update).

**Authentication**: Required (JWT Bearer token)

**Request**:
```http
PATCH /users/profile
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
    "display_name": "New Display Name",
    "profile_picture_url": "https://example.com/new-avatar.jpg"
}
```

**Supported Fields**:
- `username` (string, max 50 chars, must be unique)
- `display_name` (string, max 50 chars, can be null)
- `profile_picture_url` (string, max 255 chars, can be null)

**Response**:
```json
{
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "username": "johndoe",
    "display_name": "New Display Name",
    "profile_picture_url": "https://example.com/new-avatar.jpg",
    "created_at": "2025-01-21T10:30:00Z",
    "updated_at": "2025-01-21T15:50:00Z"
}
```

## Legacy Endpoints (Deprecated)

For backward compatibility, the following endpoints are still available:

- `GET /users/me` - Use `GET /users/profile` instead
- `PUT /users/me` - Use `PATCH /users/profile` instead

## Validation Rules

### Username
- Must be unique across all users
- Maximum 50 characters
- Cannot be empty or only whitespace
- Must not be already taken by another user

### Display Name
- Maximum 50 characters
- Can be null or empty (will be set to null)
- Cannot be only whitespace

### Profile Picture URL
- Maximum 255 characters
- Can be null (will clear the profile picture)
- Should be a valid URL format (frontend validation recommended)

## Error Handling

### 400 Bad Request
```json
{
    "detail": "Username already exists"
}
```

Common validation errors:
- "Username already exists"
- "Display name cannot be empty"
- "Display name must be 50 characters or less"
- "Username must be 50 characters or less"
- "Profile picture URL must be 255 characters or less"

### 401 Unauthorized
```json
{
    "detail": "Could not validate credentials"
}
```

Occurs when:
- No JWT token provided
- Invalid JWT token
- Expired JWT token
- Blacklisted JWT token

### 404 Not Found
```json
{
    "detail": "User not found"
}
```

Occurs when the authenticated user no longer exists in the database.

## Service Implementation

### UserService.update_user_profile()

Enhanced profile update method with specific validation:

```python
async def update_user_profile(
    session: AsyncSession, user_id: UUIDType, profile_data: UserUpdate
) -> Optional[User]:
    """Update user profile with validation for profile-specific fields."""
```

**Features**:
- Field-specific validation
- Partial updates (only provided fields are updated)
- Username uniqueness checking
- Input sanitization (trimming whitespace)
- Comprehensive error messages

### UserService.get_user_profile_summary()

Profile summary method for quick profile information:

```python
async def get_user_profile_summary(
    session: AsyncSession, user_id: UUIDType
) -> Optional[dict]:
    """Get a summary of user profile information."""
```

## Usage Examples

### Frontend Integration

```javascript
// Get user profile
const getProfile = async () => {
    const response = await fetch('/users/profile', {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    });
    return response.json();
};

// Update profile
const updateProfile = async (profileData) => {
    const response = await fetch('/users/profile', {
        method: 'PATCH',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(profileData)
    });
    return response.json();
};

// Example usage
updateProfile({
    display_name: "New Name",
    profile_picture_url: "https://example.com/pic.jpg"
});
```

### Python Client

```python
import httpx

class UserProfileClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def get_profile(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/profile",
                headers=self.headers
            )
            return response.json()
    
    async def update_profile(self, **profile_data):
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/users/profile",
                headers=self.headers,
                json=profile_data
            )
            return response.json()
```

## Testing

Run the comprehensive test script to validate the implementation:

```bash
cd backend
python test_user_profile.py
```

The test script covers:
- Profile creation and retrieval
- Partial updates with single fields
- Multiple field updates
- Validation error handling
- JWT token integration
- API usage examples

## Security Considerations

1. **Authentication Required**: All profile endpoints require valid JWT authentication
2. **User Isolation**: Users can only access and modify their own profiles
3. **Input Validation**: All input is validated and sanitized
4. **SQL Injection Protection**: Using SQLAlchemy ORM with parameterized queries
5. **Token Blacklisting**: Support for JWT token blacklisting via Redis

## Performance

- **Database Queries**: Optimized with single queries for updates
- **Connection Pooling**: Async connection pooling for scalability
- **Caching Ready**: Profile data can be cached in Redis for high-traffic scenarios
- **Partial Updates**: Only modified fields are updated in the database

## Why Profile Service is Next

1. **Builds on Authentication**: Requires JWT tokens, demonstrating security integration
2. **User Personalization**: Essential before room/message features for user identity
3. **Simple CRUD**: Straightforward operations that build confidence
4. **Testing Foundation**: Provides endpoints to test authentication flow
5. **Frontend Ready**: Clean API for frontend profile management features

## Next Steps

After implementing the User Profile Service, the application will be ready for:
1. **Room Management**: Users can create/join chat rooms with personalized profiles
2. **Message System**: Messages will include user profile information
3. **Notifications**: Profile data will be used in notification displays
4. **Advanced Features**: Avatar uploads, profile themes, etc.
