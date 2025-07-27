"""
Test script demonstrating the Room Service functionality.
This script shows how to use all room management endpoints.
"""
import asyncio
import json
from uuid import uuid4

from realtime_messaging.db.depends import sessionmanager
from realtime_messaging.models.user import UserCreate
from realtime_messaging.models.chat_room import ChatRoomCreate
from realtime_messaging.services.user_service import UserService
from realtime_messaging.services.room_service import RoomService
from realtime_messaging.services.auth import AuthService


async def test_room_service_operations():
    """Test comprehensive room service operations."""
    # Initialize the database
    sessionmanager.init_db()
    
    try:
        async for session in sessionmanager.get_session():
            print("=== Room Service Test ===\n")
            
            # 1. Create test users
            print("1. Creating test users...")
            
            creator_data = UserCreate(
                email=f"creator{uuid4().hex[:8]}@example.com",
                username=f"creator{uuid4().hex[:8]}",
                password="password123",
                display_name="Room Creator",
                profile_picture_url="https://example.com/creator.jpg"
            )
            
            participant_data = UserCreate(
                email=f"participant{uuid4().hex[:8]}@example.com",
                username=f"participant{uuid4().hex[:8]}",
                password="password123",
                display_name="Room Participant",
                profile_picture_url="https://example.com/participant.jpg"
            )
            
            invitee_data = UserCreate(
                email=f"invitee{uuid4().hex[:8]}@example.com",
                username=f"invitee{uuid4().hex[:8]}",
                password="password123",
                display_name="Room Invitee",
                profile_picture_url="https://example.com/invitee.jpg"
            )
            
            try:
                creator = await UserService.create_user(session, creator_data)
                participant = await UserService.create_user(session, participant_data)
                invitee = await UserService.create_user(session, invitee_data)
                
                print(f"✅ Created users:")
                print(f"   Creator: {creator.username} ({creator.email})")
                print(f"   Participant: {participant.username} ({participant.email})")
                print(f"   Invitee: {invitee.username} ({invitee.email})")
                print()
                
            except ValueError as e:
                print(f"❌ Error creating users: {e}")
                return
            
            # 2. Create a room
            print("2. Creating a chat room...")
            room_data = ChatRoomCreate(name="Test Room")
            
            try:
                room = await RoomService.create_room(session, room_data, creator.user_id)
                print(f"✅ Room created successfully:")
                print(f"   Room ID: {room.room_id}")
                print(f"   Name: {room.name}")
                print(f"   Creator: {room.creator_id}")
                print(f"   Created: {room.created_at}")
                print()
                
            except ValueError as e:
                print(f"❌ Error creating room: {e}")
                return
            
            # 3. Test getting room details
            print("3. Getting room details...")
            room_details = await RoomService.get_room_with_participant_count(session, room.room_id)
            if room_details:
                print(f"✅ Room details retrieved:")
                print(f"   Name: {room_details['name']}")
                print(f"   Participant Count: {room_details['participant_count']}")
                print()
            
            # 4. Test getting room participants (should have creator)
            print("4. Getting initial room participants...")
            participants = await RoomService.get_room_participants(session, room.room_id, use_cache=False)
            print(f"✅ Initial participants ({len(participants)}):")
            for p in participants:
                print(f"   - {p['username']} ({p['display_name']}) joined {p['joined_at']}")
            print()
            
            # 5. Test joining room
            print("5. Testing room join...")
            join_success = await RoomService.join_room(session, room.room_id, participant.user_id)
            if join_success:
                print(f"✅ {participant.username} joined the room successfully")
                
                # Check updated participants
                participants = await RoomService.get_room_participants(session, room.room_id, use_cache=False)
                print(f"   Updated participant count: {len(participants)}")
                print()
            
            # 6. Test duplicate join (should not fail)
            print("6. Testing duplicate join...")
            join_again = await RoomService.join_room(session, room.room_id, participant.user_id)
            if join_again:
                print(f"✅ Duplicate join handled correctly (user was already a participant)")
                print()
            
            # 7. Test checking participant status
            print("7. Testing participant status checks...")
            is_creator_participant = await RoomService.is_user_participant(session, room.room_id, creator.user_id)
            is_participant_participant = await RoomService.is_user_participant(session, room.room_id, participant.user_id)
            is_invitee_participant = await RoomService.is_user_participant(session, room.room_id, invitee.user_id)
            
            print(f"   Creator is participant: {is_creator_participant}")
            print(f"   Participant is participant: {is_participant_participant}")
            print(f"   Invitee is participant: {is_invitee_participant}")
            print()
            
            # 8. Test room invitation
            print("8. Testing room invitation...")
            try:
                invite_success = await RoomService.invite_user_to_room(
                    session, room.room_id, creator.user_id, invitee.email
                )
                if invite_success:
                    print(f"✅ Invitation sent to {invitee.email}")
                    print()
            except ValueError as e:
                print(f"❌ Invitation failed: {e}")
                print()
            
            # 9. Test getting user's rooms
            print("9. Testing get user rooms...")
            creator_rooms = await RoomService.get_user_rooms(session, creator.user_id)
            participant_rooms = await RoomService.get_user_rooms(session, participant.user_id)
            
            print(f"   Creator's rooms: {len(creator_rooms)}")
            for r in creator_rooms:
                print(f"     - {r.name} (ID: {r.room_id})")
            
            print(f"   Participant's rooms: {len(participant_rooms)}")
            for r in participant_rooms:
                print(f"     - {r.name} (ID: {r.room_id})")
            print()
            
            # 10. Test room update (only creator can update)
            print("10. Testing room update...")
            try:
                updated_room = await RoomService.update_room(
                    session, room.room_id, creator.user_id, {"name": "Updated Test Room"}
                )
                if updated_room:
                    print(f"✅ Room updated by creator: {updated_room.name}")
                    print()
            except ValueError as e:
                print(f"❌ Room update failed: {e}")
                print()
            
            # 11. Test unauthorized room update
            print("11. Testing unauthorized room update...")
            try:
                await RoomService.update_room(
                    session, room.room_id, participant.user_id, {"name": "Unauthorized Update"}
                )
                print("❌ Unauthorized update should have failed!")
            except ValueError as e:
                print(f"✅ Unauthorized update correctly rejected: {e}")
                print()
            
            # 12. Test leaving room
            print("12. Testing room leave...")
            leave_success = await RoomService.leave_room(session, room.room_id, participant.user_id)
            if leave_success:
                print(f"✅ {participant.username} left the room successfully")
                
                # Check updated participants
                participants = await RoomService.get_room_participants(session, room.room_id, use_cache=False)
                print(f"   Updated participant count: {len(participants)}")
                for p in participants:
                    print(f"   - {p['username']} ({p['display_name']})")
                print()
            
            # 13. Test Redis caching
            print("13. Testing Redis caching...")
            # First call (from database)
            participants_1 = await RoomService.get_room_participants(session, room.room_id, use_cache=True)
            # Second call (from cache)
            participants_2 = await RoomService.get_room_participants(session, room.room_id, use_cache=True)
            
            print(f"✅ Caching test completed:")
            print(f"   First call participants: {len(participants_1)}")
            print(f"   Second call participants: {len(participants_2)}")
            print(f"   Results match: {len(participants_1) == len(participants_2)}")
            print()
            
            # 14. Test error cases
            print("14. Testing error cases...")
            
            # Try to join non-existent room
            try:
                fake_room_id = uuid4()
                await RoomService.join_room(session, fake_room_id, participant.user_id)
                print("❌ Should not be able to join non-existent room")
            except ValueError:
                print("✅ Correctly rejected join to non-existent room")
            
            # Try to invite to non-existent room
            try:
                fake_room_id = uuid4()
                await RoomService.invite_user_to_room(
                    session, fake_room_id, creator.user_id, participant.email
                )
                print("❌ Should not be able to invite to non-existent room")
            except ValueError:
                print("✅ Correctly rejected invite to non-existent room")
            
            # Try to invite non-existent user
            try:
                await RoomService.invite_user_to_room(
                    session, room.room_id, creator.user_id, "nonexistent@example.com"
                )
                print("❌ Should not be able to invite non-existent user")
            except ValueError:
                print("✅ Correctly rejected invite to non-existent user")
            
            print()
            
            # 15. Create JWT tokens for API testing
            print("15. Creating JWT tokens for API testing...")
            creator_tokens = AuthService.create_tokens_for_user(creator)
            participant_tokens = AuthService.create_tokens_for_user(participant)
            
            print(f"✅ JWT tokens created:")
            print(f"   Creator token (first 50 chars): {creator_tokens['access_token'][:50]}...")
            print(f"   Participant token (first 50 chars): {participant_tokens['access_token'][:50]}...")
            print()
            
            print("=== Room Service Test Completed Successfully! ===")
            print(f"Created room ID for API testing: {room.room_id}")
            print(f"Creator email: {creator.email}")
            print(f"Participant email: {participant.email}")
            print(f"Invitee email: {invitee.email}")
            
            break  # Exit the async generator loop
            
    finally:
        # Clean up
        await sessionmanager.close()
        print("\nDatabase connections closed.")


async def demo_api_usage():
    """Demonstrate API usage examples."""
    print("\n=== API Usage Examples ===\n")
    
    print("Room Management API Examples:")
    print()
    
    print("1. Create Room:")
    print("   POST /rooms")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print("   Body:", json.dumps({"name": "My Chat Room"}, indent=2))
    print()
    
    print("2. Get User's Rooms:")
    print("   GET /rooms")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print()
    
    print("3. Get Room Details:")
    print("   GET /rooms/{room_id}")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print()
    
    print("4. Update Room:")
    print("   PUT /rooms/{room_id}")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print("   Body:", json.dumps({"name": "Updated Room Name"}, indent=2))
    print()
    
    print("5. Invite User:")
    print("   POST /rooms/{room_id}/invite")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print("   Body:", json.dumps({"email": "user@example.com"}, indent=2))
    print()
    
    print("6. Join Room:")
    print("   POST /rooms/{room_id}/join")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print()
    
    print("7. Leave Room:")
    print("   POST /rooms/{room_id}/leave")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print()
    
    print("8. Get Room Participants:")
    print("   GET /rooms/{room_id}/participants")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print()
    
    print("9. Delete Room (Creator Only):")
    print("   DELETE /rooms/{room_id}")
    print("   Headers: Authorization: Bearer <jwt_token>")
    print()


if __name__ == "__main__":
    print("Running Room Service tests...")
    asyncio.run(test_room_service_operations())
    asyncio.run(demo_api_usage())
