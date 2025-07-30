"""
Example script demonstrating how to use the database connection and user service.
This script shows how to create users and retrieve them using the async session.
"""

import asyncio
from uuid import uuid4

from realtime_messaging.db.depends import sessionmanager
from realtime_messaging.models.user import UserCreate
from realtime_messaging.services.user_service import UserService


async def example_user_operations():
    """Example function showing user operations."""
    # Initialize the database
    sessionmanager.init_db()

    try:
        # Get a database session
        async for session in sessionmanager.get_session():
            print("=== User Operations Example ===\n")

            # Create a new user
            user_data = UserCreate(
                email="john.doe@example.com",
                username="johndoe",
                password="securepassword123",
                display_name="John Doe",
                profile_picture_url="https://example.com/avatar.jpg",
            )

            print("Creating a new user...")
            try:
                new_user = await UserService.create_user(session, user_data)
                print(f"✅ User created successfully!")
                print(f"   ID: {new_user.user_id}")
                print(f"   Email: {new_user.email}")
                print(f"   Username: {new_user.username}")
                print(f"   Display Name: {new_user.display_name}")
                print(f"   Created At: {new_user.created_at}")
                print()

                # Get user by ID
                print("Retrieving user by ID...")
                retrieved_user = await UserService.get_user_by_id(
                    session, new_user.user_id
                )
                if retrieved_user:
                    print(f"✅ User found: {retrieved_user.username}")
                else:
                    print("❌ User not found")
                print()

                # Get user by email
                print("Retrieving user by email...")
                user_by_email = await UserService.get_user_by_email(
                    session, "john.doe@example.com"
                )
                if user_by_email:
                    print(f"✅ User found by email: {user_by_email.username}")
                else:
                    print("❌ User not found by email")
                print()

                # Get user by username
                print("Retrieving user by username...")
                user_by_username = await UserService.get_user_by_username(
                    session, "johndoe"
                )
                if user_by_username:
                    print(f"✅ User found by username: {user_by_username.email}")
                else:
                    print("❌ User not found by username")
                print()

                # Authenticate user
                print("Authenticating user...")
                authenticated_user = await UserService.authenticate_user(
                    session, "john.doe@example.com", "securepassword123"
                )
                if authenticated_user:
                    print(
                        f"✅ Authentication successful for: {authenticated_user.username}"
                    )
                else:
                    print("❌ Authentication failed")
                print()

                # Try to authenticate with wrong password
                print("Trying authentication with wrong password...")
                wrong_auth = await UserService.authenticate_user(
                    session, "john.doe@example.com", "wrongpassword"
                )
                if wrong_auth:
                    print(
                        "❌ This shouldn't happen - authentication with wrong password succeeded"
                    )
                else:
                    print("✅ Authentication correctly failed with wrong password")
                print()

            except ValueError as e:
                print(f"❌ Error creating user: {e}")
                print(
                    "This might happen if you run the script multiple times with the same email/username"
                )

            break  # Exit the async generator loop

    finally:
        # Clean up
        await sessionmanager.close()
        print("Database connections closed.")


if __name__ == "__main__":
    print("Running user operations example...")
    asyncio.run(example_user_operations())
