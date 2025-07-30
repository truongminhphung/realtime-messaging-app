#!/usr/bin/env python3
"""
Test script to verify that all imports work correctly.
"""


def test_imports():
    """Test that all critical imports work without errors."""
    print("Testing imports...")

    try:
        # Test main FastAPI app import
        from realtime_messaging.main import app

        print("✅ Main app import successful")
    except ImportError as e:
        print(f"❌ Main app import failed: {e}")
        return False

    try:
        # Test database dependencies
        from realtime_messaging.db.depends import get_db, sessionmanager

        print("✅ Database dependencies import successful")
    except ImportError as e:
        print(f"❌ Database dependencies import failed: {e}")
        return False

    try:
        # Test notification routes
        from realtime_messaging.routes.notifications import router

        print("✅ Notification routes import successful")
    except ImportError as e:
        print(f"❌ Notification routes import failed: {e}")
        return False

    try:
        # Test notification service
        from realtime_messaging.services.notification_service import NotificationService

        print("✅ Notification service import successful")
    except ImportError as e:
        print(f"❌ Notification service import failed: {e}")
        return False

    try:
        # Test notification models
        from realtime_messaging.models.notification import (
            NotificationGet,
            NotificationType,
            NotificationStatus,
        )

        print("✅ Notification models import successful")
    except ImportError as e:
        print(f"❌ Notification models import failed: {e}")
        return False

    try:
        # Test dependencies
        from realtime_messaging.dependencies import get_current_user

        print("✅ Dependencies import successful")
    except ImportError as e:
        print(f"❌ Dependencies import failed: {e}")
        return False

    print("🎉 All imports successful!")
    return True


if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n✅ Import test passed - no import errors detected!")
    else:
        print("\n❌ Import test failed - there are import errors!")
        exit(1)
