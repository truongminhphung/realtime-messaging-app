"""
Example script demonstrating how to use the authentication system.
This script shows how to register, login, and make authenticated requests.
"""
import asyncio
import httpx
from uuid import uuid4


async def test_authentication():
    """Test the authentication endpoints."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        print("=== Authentication System Test ===\n")
        
        # Generate unique test data
        test_email = f"testuser_{uuid4().hex[:8]}@example.com"
        test_username = f"testuser_{uuid4().hex[:8]}"
        test_password = "securepassword123"
        
        print(f"Testing with email: {test_email}")
        print(f"Testing with username: {test_username}\n")
        
        # 1. Register a new user
        print("1. Testing user registration...")
        register_data = {
            "email": test_email,
            "username": test_username,
            "password": test_password,
            "display_name": "Test User",
            "profile_picture_url": "https://example.com/avatar.jpg"
        }
        
        response = await client.post(f"{base_url}/auth/register", json=register_data)
        if response.status_code == 201:
            print("✅ Registration successful!")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return
        print()
        
        # 2. Login with the registered user
        print("2. Testing user login...")
        login_data = {
            "email": test_email,
            "password": test_password
        }
        
        response = await client.post(f"{base_url}/auth/login", json=login_data)
        if response.status_code == 200:
            login_response = response.json()
            access_token = login_response["access_token"]
            print("✅ Login successful!")
            print(f"   Token type: {login_response['token_type']}")
            print(f"   Expires in: {login_response['expires_in']} seconds")
            print(f"   User ID: {login_response['user']['user_id']}")
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return
        print()
        
        # 3. Test protected endpoint - get current user
        print("3. Testing protected endpoint - /auth/me...")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await client.get(f"{base_url}/auth/me", headers=headers)
        if response.status_code == 200:
            print("✅ Protected endpoint access successful!")
            print(f"   User info: {response.json()}")
        else:
            print(f"❌ Protected endpoint failed: {response.status_code} - {response.text}")
        print()
        
        # 4. Test token verification
        print("4. Testing token verification...")
        response = await client.post(f"{base_url}/auth/verify-token", headers=headers)
        if response.status_code == 200:
            print("✅ Token verification successful!")
            print(f"   Verification result: {response.json()}")
        else:
            print(f"❌ Token verification failed: {response.status_code} - {response.text}")
        print()
        
        # 5. Test user profile endpoints
        print("5. Testing user profile endpoints...")
        response = await client.get(f"{base_url}/users/me", headers=headers)
        if response.status_code == 200:
            print("✅ User profile retrieval successful!")
            user_data = response.json()
            print(f"   User profile: {user_data}")
            
            # Test profile update
            update_data = {
                "display_name": "Updated Test User"
            }
            response = await client.put(f"{base_url}/users/me", json=update_data, headers=headers)
            if response.status_code == 200:
                print("✅ User profile update successful!")
                print(f"   Updated profile: {response.json()}")
            else:
                print(f"❌ Profile update failed: {response.status_code} - {response.text}")
        else:
            print(f"❌ User profile retrieval failed: {response.status_code} - {response.text}")
        print()
        
        # 6. Test accessing protected endpoint without token
        print("6. Testing protected endpoint without token...")
        response = await client.get(f"{base_url}/auth/me")
        if response.status_code == 401:
            print("✅ Correctly rejected request without token!")
        else:
            print(f"❌ Should have rejected request without token: {response.status_code}")
        print()
        
        # 7. Test logout
        print("7. Testing logout...")
        response = await client.post(f"{base_url}/auth/logout", headers=headers)
        if response.status_code == 200:
            print("✅ Logout successful!")
            print(f"   Response: {response.json()}")
            
            # Test using token after logout
            print("   Testing token after logout...")
            response = await client.get(f"{base_url}/auth/me", headers=headers)
            if response.status_code == 401:
                print("✅ Token correctly invalidated after logout!")
            else:
                print(f"❌ Token should be invalid after logout: {response.status_code}")
        else:
            print(f"❌ Logout failed: {response.status_code} - {response.text}")
        print()
        
        # 8. Test login with wrong password
        print("8. Testing login with wrong password...")
        wrong_login_data = {
            "email": test_email,
            "password": "wrongpassword"
        }
        
        response = await client.post(f"{base_url}/auth/login", json=wrong_login_data)
        if response.status_code == 401:
            print("✅ Correctly rejected wrong password!")
        else:
            print(f"❌ Should have rejected wrong password: {response.status_code}")
        print()
        
        print("=== Authentication Test Complete ===")


if __name__ == "__main__":
    print("Starting authentication test...")
    print("Make sure the FastAPI server is running on http://localhost:8000")
    print("You can start it with: uvicorn app.main:app --reload")
    print()
    
    try:
        asyncio.run(test_authentication())
    except httpx.ConnectError:
        print("❌ Could not connect to the server. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
