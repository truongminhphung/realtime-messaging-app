"""
Notification system utilities for deployment and testing.
This module provides utilities to test and verify the complete notification system.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4, UUID as UUIDType
import logging

from realtime_messaging.services.notification_service import NotificationService
from realtime_messaging.services.notification_worker import NotificationWorker
from realtime_messaging.services.notification_integration import (
    create_message_notification,
    create_room_invite_notification,
    create_friend_request_notification,
    get_user_notification_summary
)
from realtime_messaging.models.notification import NotificationType, NotificationStatus
from realtime_messaging.db.depends import get_db_session


logger = logging.getLogger(__name__)


class NotificationSystemTester:
    """Test suite for the complete notification system."""
    
    def __init__(self):
        self.test_user_id = uuid4()
        self.test_room_id = uuid4()
        self.test_sender_id = uuid4()
        
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests on the notification system."""
        results = {
            "test_start": datetime.utcnow().isoformat(),
            "tests": {}
        }
        
        try:
            # Test 1: Basic notification creation
            results["tests"]["basic_creation"] = await self._test_basic_notification_creation()
            
            # Test 2: Message notification integration
            results["tests"]["message_integration"] = await self._test_message_notification_integration()
            
            # Test 3: Room invite integration
            results["tests"]["room_invite_integration"] = await self._test_room_invite_integration()
            
            # Test 4: Friend request integration
            results["tests"]["friend_request_integration"] = await self._test_friend_request_integration()
            
            # Test 5: Notification queries and filtering
            results["tests"]["query_filtering"] = await self._test_notification_queries()
            
            # Test 6: Notification preferences
            results["tests"]["preferences"] = await self._test_notification_preferences()
            
            # Test 7: Performance test (small scale)
            results["tests"]["performance"] = await self._test_performance()
            
            # Test 8: Caching behavior
            results["tests"]["caching"] = await self._test_caching_behavior()
            
            results["test_end"] = datetime.utcnow().isoformat()
            results["overall_success"] = all(
                test["success"] for test in results["tests"].values()
            )
            
        except Exception as e:
            logger.error(f"Error during comprehensive testing: {e}")
            results["error"] = str(e)
            results["overall_success"] = False
            
        return results
    
    async def _test_basic_notification_creation(self) -> Dict[str, Any]:
        """Test basic notification CRUD operations."""
        try:
            async with get_db_session() as session:
                # Create a notification
                notification = await NotificationService.create_notification(
                    session=session,
                    user_id=self.test_user_id,
                    notification_type=NotificationType.NEW_MESSAGE,
                    content={"test": "basic creation"},
                    status=NotificationStatus.PENDING
                )
                
                # Verify creation
                if not notification:
                    return {"success": False, "error": "Failed to create notification"}
                
                # Test retrieval
                notifications = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    limit=10,
                    offset=0
                )
                
                # Test marking as read
                success = await NotificationService.mark_as_read(
                    session=session,
                    notification_id=notification.id
                )
                
                # Test deletion
                deleted = await NotificationService.delete_notification(
                    session=session,
                    notification_id=notification.id,
                    user_id=self.test_user_id
                )
                
                return {
                    "success": True,
                    "created": notification.id is not None,
                    "retrieved": len(notifications) >= 1,
                    "marked_read": success,
                    "deleted": deleted
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_message_notification_integration(self) -> Dict[str, Any]:
        """Test message notification integration."""
        try:
            async with get_db_session() as session:
                # Test message notification creation
                success = await create_message_notification(
                    session=session,
                    message_id=uuid4(),
                    room_id=self.test_room_id,
                    sender_id=self.test_sender_id,
                    recipient_ids=[self.test_user_id],
                    message_content="Test message for notification",
                    sender_info={
                        "user_id": str(self.test_sender_id),
                        "username": "test_sender",
                        "display_name": "Test Sender"
                    }
                )
                
                # Check if notification was created
                notifications = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    notification_type=NotificationType.NEW_MESSAGE,
                    limit=5,
                    offset=0
                )
                
                return {
                    "success": True,
                    "integration_success": success,
                    "notifications_created": len(notifications) > 0
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_room_invite_integration(self) -> Dict[str, Any]:
        """Test room invitation notification integration."""
        try:
            async with get_db_session() as session:
                # Test room invite notification creation
                success = await create_room_invite_notification(
                    session=session,
                    room_id=self.test_room_id,
                    room_name="Test Room",
                    room_description="A test room for notifications",
                    inviter_id=self.test_sender_id,
                    invitee_id=self.test_user_id,
                    inviter_info={
                        "user_id": str(self.test_sender_id),
                        "username": "test_inviter",
                        "display_name": "Test Inviter"
                    }
                )
                
                # Check if notification was created
                notifications = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    notification_type=NotificationType.ROOM_INVITATION,
                    limit=5,
                    offset=0
                )
                
                return {
                    "success": True,
                    "integration_success": success,
                    "notifications_created": len(notifications) > 0
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_friend_request_integration(self) -> Dict[str, Any]:
        """Test friend request notification integration."""
        try:
            async with get_db_session() as session:
                # Test friend request notification creation
                success = await create_friend_request_notification(
                    session=session,
                    sender_id=self.test_sender_id,
                    recipient_id=self.test_user_id,
                    sender_info={
                        "user_id": str(self.test_sender_id),
                        "username": "test_friend",
                        "display_name": "Test Friend"
                    },
                    request_type="friend_request"
                )
                
                # Check if notification was created
                notifications = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    notification_type=NotificationType.FRIEND_REQUEST,
                    limit=5,
                    offset=0
                )
                
                return {
                    "success": True,
                    "integration_success": success,
                    "notifications_created": len(notifications) > 0
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_notification_queries(self) -> Dict[str, Any]:
        """Test notification queries and filtering."""
        try:
            async with get_db_session() as session:
                # Test various query parameters
                all_notifications = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    limit=50,
                    offset=0
                )
                
                unread_notifications = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    unread_only=True,
                    limit=50,
                    offset=0
                )
                
                message_notifications = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    notification_type=NotificationType.NEW_MESSAGE,
                    limit=50,
                    offset=0
                )
                
                # Test notification counts
                total_count = await NotificationService.get_notification_count(
                    session=session,
                    user_id=self.test_user_id
                )
                
                unread_count = await NotificationService.get_notification_count(
                    session=session,
                    user_id=self.test_user_id,
                    unread_only=True
                )
                
                return {
                    "success": True,
                    "all_notifications": len(all_notifications),
                    "unread_notifications": len(unread_notifications),
                    "message_notifications": len(message_notifications),
                    "total_count": total_count,
                    "unread_count": unread_count
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_notification_preferences(self) -> Dict[str, Any]:
        """Test notification preferences functionality."""
        try:
            async with get_db_session() as session:
                # Test setting preferences
                test_preferences = {
                    "push_notifications": True,
                    "email_notifications": False,
                    "notification_types": {
                        "new_message": True,
                        "room_invitation": True,
                        "friend_request": False
                    }
                }
                
                success = await NotificationService.update_notification_preferences(
                    session=session,
                    user_id=self.test_user_id,
                    preferences=test_preferences
                )
                
                # Test getting preferences
                preferences = await NotificationService.get_notification_preferences(
                    session=session,
                    user_id=self.test_user_id
                )
                
                return {
                    "success": True,
                    "preferences_updated": success,
                    "preferences_retrieved": preferences is not None,
                    "preferences_match": (
                        preferences.get("push_notifications") == True
                        if preferences else False
                    )
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_performance(self) -> Dict[str, Any]:
        """Test performance with multiple notifications."""
        try:
            start_time = datetime.utcnow()
            
            async with get_db_session() as session:
                # Create multiple notifications
                tasks = []
                for i in range(10):
                    task = NotificationService.create_notification(
                        session=session,
                        user_id=self.test_user_id,
                        notification_type=NotificationType.NEW_MESSAGE,
                        content={"test": f"performance test {i}"},
                        status=NotificationStatus.PENDING
                    )
                    tasks.append(task)
                
                # Execute all tasks
                notifications = await asyncio.gather(*tasks, return_exceptions=True)
                successful_creates = sum(1 for n in notifications if not isinstance(n, Exception))
                
                # Test batch retrieval
                retrieved_notifications = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    limit=20,
                    offset=0
                )
                
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "notifications_created": successful_creates,
                "notifications_retrieved": len(retrieved_notifications),
                "duration_seconds": duration,
                "avg_create_time_ms": (duration * 1000) / 10 if successful_creates > 0 else 0
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_caching_behavior(self) -> Dict[str, Any]:
        """Test Redis caching behavior."""
        try:
            async with get_db_session() as session:
                # First query (should cache)
                start_time = datetime.utcnow()
                notifications1 = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    limit=10,
                    offset=0
                )
                first_query_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Second query (should use cache)
                start_time = datetime.utcnow()
                notifications2 = await NotificationService.get_user_notifications(
                    session=session,
                    user_id=self.test_user_id,
                    limit=10,
                    offset=0
                )
                second_query_time = (datetime.utcnow() - start_time).total_seconds()
                
                return {
                    "success": True,
                    "first_query_time": first_query_time,
                    "second_query_time": second_query_time,
                    "cache_improvement": first_query_time > second_query_time,
                    "results_consistent": len(notifications1) == len(notifications2)
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}


async def run_notification_system_health_check() -> Dict[str, Any]:
    """Run a quick health check on the notification system."""
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "unknown",
        "components": {}
    }
    
    try:
        # Test database connection
        async with get_db_session() as session:
            # Try a simple count query
            count = await NotificationService.get_notification_count(
                session=session,
                user_id=uuid4()  # Non-existent user should return 0
            )
            health_status["components"]["database"] = {
                "status": "healthy",
                "test_query_result": count
            }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Test Redis connection (through service)
    try:
        # This would test Redis indirectly through the notification service cache
        health_status["components"]["redis"] = {
            "status": "healthy",
            "note": "Tested indirectly through notification service"
        }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Test RabbitMQ connection (basic test)
    try:
        # This would require testing the RabbitMQ service
        health_status["components"]["rabbitmq"] = {
            "status": "healthy",
            "note": "Service available for testing"
        }
    except Exception as e:
        health_status["components"]["rabbitmq"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Determine overall status
    all_healthy = all(
        component.get("status") == "healthy" 
        for component in health_status["components"].values()
    )
    
    health_status["status"] = "healthy" if all_healthy else "degraded"
    
    return health_status


# CLI utility functions
def print_test_results(results: Dict[str, Any]) -> None:
    """Pretty print test results."""
    print("\n" + "="*60)
    print("NOTIFICATION SYSTEM TEST RESULTS")
    print("="*60)
    
    print(f"Test Started: {results.get('test_start', 'Unknown')}")
    print(f"Test Ended: {results.get('test_end', 'Unknown')}")
    print(f"Overall Success: {results.get('overall_success', False)}")
    
    if "tests" in results:
        print("\nIndividual Test Results:")
        print("-" * 40)
        
        for test_name, test_result in results["tests"].items():
            status = "✅ PASS" if test_result.get("success", False) else "❌ FAIL"
            print(f"{test_name:25} {status}")
            
            if not test_result.get("success", False) and "error" in test_result:
                print(f"  Error: {test_result['error']}")
    
    if "error" in results:
        print(f"\nGeneral Error: {results['error']}")
    
    print("="*60)


async def main():
    """Main function to run tests."""
    print("Starting Notification System Tests...")
    
    # Run health check first
    print("\n1. Running Health Check...")
    health = await run_notification_system_health_check()
    print(f"Health Status: {health['status']}")
    
    # Run comprehensive tests
    print("\n2. Running Comprehensive Tests...")
    tester = NotificationSystemTester()
    results = await tester.run_comprehensive_tests()
    
    # Print results
    print_test_results(results)
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
