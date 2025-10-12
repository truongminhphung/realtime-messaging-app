from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from realtime_messaging.websocket.notification_endpoints import (
    websocket_notifications_endpoint,
)

# WebSocket router for notifications
router = APIRouter(prefix="/ws", tags=["websocket", "notifications"])


@router.websocket("/test-simple")
async def websocket_test_simple(websocket: WebSocket):
    """Simple test WebSocket without authentication"""
    try:
        await websocket.accept()
        await websocket.send_text("Hello from simple WebSocket!")

        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
                else:
                    await websocket.send_text(f"Echo: {data}")
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket message error: {e}")
                break

    except Exception as e:
        print(f"WebSocket connection error: {e}")
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications.

    Authentication is handled via JWT token passed as query parameter.
    Example: ws://localhost:8000/ws/notifications?token=your_jwt_token

    Note: Query parameter handling for WebSocket in FastAPI routers can be tricky.
    This endpoint now handles token extraction manually from the query string.
    """
    try:
        # Extract token from query parameters manually
        query_params = dict(websocket.query_params)
        token = query_params.get("token")

        if not token:
            await websocket.close(code=4000, reason="Token required")
            return
        await websocket_notifications_endpoint(websocket, token)

    except Exception as e:
        print(f"WebSocket notifications error: {e}")
        try:
            await websocket.close(code=4001, reason="Authentication failed")
        except:
            pass
