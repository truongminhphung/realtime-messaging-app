"""
Test script to verify Pydantic validation for message content.
"""
import uuid
from pydantic import ValidationError
from realtime_messaging.models.message import MessageCreate, MessageUpdate, MessageCreateInternal

def test_message_validation():
    """Test Pydantic validation for message models."""
    
    print("Testing Pydantic Message Validation")
    print("=" * 50)
    
    # Test data
    room_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    
    # Test 1: Valid message
    try:
        valid_message = MessageCreate(
            room_id=room_id,
            sender_id=sender_id,
            content="This is a valid message"
        )
        print("✅ Valid message test passed")
        print(f"   Content: '{valid_message.content}'")
    except ValidationError as e:
        print(f"❌ Valid message test failed: {e}")
    
    # Test 2: Empty content
    try:
        MessageCreate(
            room_id=room_id,
            sender_id=sender_id,
            content=""
        )
        print("❌ Empty content test failed - should have raised ValidationError")
    except ValidationError as e:
        print("✅ Empty content test passed - correctly rejected")
        print(f"   Error: {e.errors()[0]['msg']}")
    
    # Test 3: Whitespace only content
    try:
        MessageCreate(
            room_id=room_id,
            sender_id=sender_id,
            content="   \n\t   "
        )
        print("❌ Whitespace-only content test failed - should have raised ValidationError")
    except ValidationError as e:
        print("✅ Whitespace-only content test passed - correctly rejected")
        print(f"   Error: {e.errors()[0]['msg']}")
    
    # Test 4: Content too long (>500 characters)
    long_content = "a" * 501
    try:
        MessageCreate(
            room_id=room_id,
            sender_id=sender_id,
            content=long_content
        )
        print("❌ Long content test failed - should have raised ValidationError")
    except ValidationError as e:
        print("✅ Long content test passed - correctly rejected")
        print(f"   Error: {e.errors()[0]['msg']}")
    
    # Test 5: Content with leading/trailing whitespace (should be cleaned)
    try:
        message_with_whitespace = MessageCreate(
            room_id=room_id,
            sender_id=sender_id,
            content="  Hello World  \n"
        )
        print("✅ Whitespace trimming test passed")
        print(f"   Original: '  Hello World  \\n'")
        print(f"   Cleaned:  '{message_with_whitespace.content}'")
    except ValidationError as e:
        print(f"❌ Whitespace trimming test failed: {e}")
    
    # Test 6: Exactly 500 characters (should pass)
    exact_500_chars = "a" * 500
    try:
        message_500 = MessageCreate(
            room_id=room_id,
            sender_id=sender_id,
            content=exact_500_chars
        )
        print("✅ 500-character limit test passed")
        print(f"   Length: {len(message_500.content)} characters")
    except ValidationError as e:
        print(f"❌ 500-character limit test failed: {e}")
    
    print("\nTesting MessageUpdate validation:")
    print("-" * 30)
    
    # Test 7: Valid update
    try:
        valid_update = MessageUpdate(content="Updated content")
        print("✅ Valid update test passed")
        print(f"   Content: '{valid_update.content}'")
    except ValidationError as e:
        print(f"❌ Valid update test failed: {e}")
    
    # Test 8: None content (should be allowed for MessageUpdate)
    try:
        none_update = MessageUpdate(content=None)
        print("✅ None content update test passed")
        print(f"   Content: {none_update.content}")
    except ValidationError as e:
        print(f"❌ None content update test failed: {e}")
    
    # Test 9: Empty string update (should fail)
    try:
        MessageUpdate(content="")
        print("❌ Empty string update test failed - should have raised ValidationError")
    except ValidationError as e:
        print("✅ Empty string update test passed - correctly rejected")
        print(f"   Error: {e.errors()[0]['msg']}")
    
    print("\nTesting MessageCreateInternal validation:")
    print("-" * 40)
    
    # Test 10: Valid internal message
    try:
        valid_internal = MessageCreateInternal(
            room_id=room_id,
            sender_id=sender_id,
            content="Internal message content"
        )
        print("✅ Valid internal message test passed")
        print(f"   Content: '{valid_internal.content}'")
    except ValidationError as e:
        print(f"❌ Valid internal message test failed: {e}")
    
    # Test 11: Invalid internal message
    try:
        MessageCreateInternal(
            room_id=room_id,
            sender_id=sender_id,
            content=""
        )
        print("❌ Invalid internal message test failed - should have raised ValidationError")
    except ValidationError as e:
        print("✅ Invalid internal message test passed - correctly rejected")
        print(f"   Error: {e.errors()[0]['msg']}")
    
    print("\n" + "=" * 50)
    print("Message validation tests completed!")


if __name__ == "__main__":
    test_message_validation()
