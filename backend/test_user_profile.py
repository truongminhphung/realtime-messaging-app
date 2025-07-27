"""
Test script demonstrating the User Profile Service functionality.
This script shows how to use the /profile endpoints for user profile management.
"""
import asyncio
import json
from uuid import uuid4

from realtime_messaging.db.depends import sessionmanager
from realtime_messaging.models.user import UserCreate, UserUpdate
from realtime_messaging.services.user_service import UserService
from realtime_messaging.services.auth import AuthService


async def test_user_profile_operations():
    """Test user profile operations including GET and PATCH /profile endpoints."""
    # Initialize the database
    sessionmanager.init_db()
    
    try:
        async for session in sessionmanager.get_session():
            print("=== User Profile Service Test ===\n")
            
            # 1. Create a test user first
            user_data = UserCreate(
                email=f"testuser{uuid4().hex[:8]}@example.com",
                username=f"testuser{uuid4().hex[:8]}",
                password="securepassword123",
                display_name="Test User",
                profile_picture_url="https://example.com/avatar.jpg"
            )
            
            print("1. Creating a test user...")
            try:
                new_user = await UserService.create_user(session, user_data)
                print(f"✅ User created successfully!")
                print(f"   ID: {new_user.user_id}")
                print(f"   Email: {new_user.email}")
                print(f"   Username: {new_user.username}")
                print(f"   Display Name: {new_user.display_name}")
                print()
                
                # 2. Test profile retrieval (simulating GET /profile)
                print("2. Testing profile retrieval...")
                profile = await UserService.get_user_profile_summary(session, new_user.user_id)
                if profile:
                    print(f"✅ Profile retrieved successfully:")
                    print(f"   Username: {profile['username']}")
                    print(f"   Display Name: {profile['display_name']}")
                    print(f"   Profile Picture: {profile['profile_picture_url']}")
                    print(f"   Created: {profile['created_at']}")
                else:
                    print("❌ Profile not found")
                print()
                
                # 3. Test profile update with display name (simulating PATCH /profile)
                print("3. Testing profile update - Display Name...")
                update_data = UserUpdate(display_name="Updated Display Name")
                updated_user = await UserService.update_user_profile(session, new_user.user_id, update_data)
                if updated_user:
                    print(f"✅ Display name updated successfully:")
                    print(f"   New Display Name: {updated_user.display_name}")
                    print(f"   Username (unchanged): {updated_user.username}")
                else:
                    print("❌ Profile update failed")
                print()
                
                # 4. Test profile update with profile picture
                print("4. Testing profile update - Profile Picture...")
                update_data = UserUpdate(profile_picture_url="https://example.com/new-avatar.jpg")
                updated_user = await UserService.update_user_profile(session, new_user.user_id, update_data)
                if updated_user:
                    print(f"✅ Profile picture updated successfully:")
                    print(f"   New Profile Picture: {updated_user.profile_picture_url}")
                    print(f"   Display Name (unchanged): {updated_user.display_name}")
                else:
                    print("❌ Profile picture update failed")
                print()
                
                # 5. Test username update
                new_username = f"newusername{uuid4().hex[:8]}"
                print(f"5. Testing profile update - Username to '{new_username}'...")
                update_data = UserUpdate(username=new_username)
                updated_user = await UserService.update_user_profile(session, new_user.user_id, update_data)
                if updated_user:
                    print(f"✅ Username updated successfully:")
                    print(f"   New Username: {updated_user.username}")
                    print(f"   Display Name (unchanged): {updated_user.display_name}")
                else:
                    print("❌ Username update failed")
                print()
                
                # 6. Test partial update with multiple fields
                print("6. Testing partial update with multiple fields...")
                update_data = UserUpdate(
                    display_name="Final Display Name",
                    profile_picture_url="https://example.com/final-avatar.jpg"
                )
                updated_user = await UserService.update_user_profile(session, new_user.user_id, update_data)
                if updated_user:
                    print(f"✅ Multiple fields updated successfully:")
                    print(f"   Display Name: {updated_user.display_name}")
                    print(f"   Profile Picture: {updated_user.profile_picture_url}")
                    print(f"   Username (unchanged): {updated_user.username}")
                else:
                    print("❌ Multiple field update failed")
                print()
                
                # 7. Test validation errors
                print("7. Testing validation errors...")
                
                # Empty display name
                try:
                    update_data = UserUpdate(display_name="   ")  # Empty after strip
                    await UserService.update_user_profile(session, new_user.user_id, update_data)
                    print("❌ Empty display name validation failed")
                except ValueError as e:
                    print(f"✅ Empty display name correctly rejected: {e}")
                
                # Too long display name
                try:
                    update_data = UserUpdate(display_name="x" * 51)  # Too long
                    await UserService.update_user_profile(session, new_user.user_id, update_data)
                    print("❌ Long display name validation failed")
                except ValueError as e:
                    print(f"✅ Long display name correctly rejected: {e}")
                
                # Too long profile URL
                try:
                    update_data = UserUpdate(profile_picture_url="https://example.com/" + "x" * 250)
                    await UserService.update_user_profile(session, new_user.user_id, update_data)
                    print("❌ Long URL validation failed")
                except ValueError as e:
                    print(f"✅ Long URL correctly rejected: {e}")
                print()
                
                # 8. Test JWT token creation for this user (simulating login)
                print("8. Testing JWT token creation...")
                tokens = AuthService.create_tokens_for_user(updated_user)
                print(f"✅ JWT token created successfully:")
                print(f"   Token Type: {tokens['token_type']}")
                print(f"   Expires In: {tokens['expires_in']} seconds")
                print(f"   User Info: {tokens['user']['username']} ({tokens['user']['email']})")
                print()
                
                # 9. Final profile summary
                print("9. Final profile summary...")
                final_profile = await UserService.get_user_profile_summary(session, new_user.user_id)
                if final_profile:
                    print(f"✅ Final profile state:")
                    print(json.dumps({
                        "username": final_profile['username'],
                        "display_name": final_profile['display_name'],
                        "profile_picture_url": final_profile['profile_picture_url'],
                        "created_at": final_profile['created_at'].isoformat(),
                        "updated_at": final_profile['updated_at'].isoformat()
                    }, indent=2))
                print()
                
            except ValueError as e:
                print(f"❌ Error in user operations: {e}")
            
            break  # Exit the async generator loop
            
    finally:
        # Clean up
        await sessionmanager.close()
        print("Database connections closed.")


async def demo_api_usage():
    """Demonstrate how the profile endpoints would be used in API calls."""
    print("\n=== API Usage Examples ===\n")
    
    print("Example API calls for user profile management:")
    print()
    
    print("1. GET /users/profile")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print("   Response: Complete user profile information")
    print()
    
    print("2. PATCH /users/profile")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print("   Content-Type: application/json")
    print("   Body:")
    print(json.dumps({
        "display_name": "New Display Name",
        "profile_picture_url": "https://example.com/new-avatar.jpg"
    }, indent=4))
    print("   Response: Updated user profile")
    print()
    
    print("3. Partial Update Examples:")
    print("   Update only display name:")
    print("   PATCH /users/profile")
    print("   Body:", json.dumps({"display_name": "Just Display Name"}))
    print()
    print("   Update only profile picture:")
    print("   PATCH /users/profile")
    print("   Body:", json.dumps({"profile_picture_url": "https://example.com/pic.jpg"}))
    print()
    print("   Clear profile picture:")
    print("   PATCH /users/profile")
    print("   Body:", json.dumps({"profile_picture_url": None}))
    print()


if __name__ == "__main__":
    print("Running User Profile Service tests...")
    asyncio.run(test_user_profile_operations())
    asyncio.run(demo_api_usage())
