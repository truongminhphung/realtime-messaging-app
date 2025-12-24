from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from realtime_messaging.routes import (
    auth,
    users,
    userprofiles,
    messages,
    rooms,
    notifications,
    direct_messages,
)
from realtime_messaging.websocket import chat
from realtime_messaging.websocket import notification_routes
from realtime_messaging.db.depends import sessionmanager
from realtime_messaging.services.rabbitmq import startup_rabbitmq, shutdown_rabbitmq
from .exceptions import configure_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Startup
    print("Starting up the Messaging App API...")
    sessionmanager.init_db()
    print("Database initialized successfully!")

    # Initialize RabbitMQ
    await startup_rabbitmq()
    print("RabbitMQ initialized successfully!")

    yield

    # Shutdown
    print("Shutting down the Messaging App API...")
    await sessionmanager.close()
    await shutdown_rabbitmq()
    print("Database connections and RabbitMQ closed.")


app = FastAPI(lifespan=lifespan)

# Configure error handlers
configure_error_handlers(app)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(userprofiles.router)
app.include_router(messages.router)
app.include_router(direct_messages.router)
app.include_router(rooms.router)
app.include_router(notifications.router)
# app.include_router(chat.router)
app.include_router(notification_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Test WebSocket endpoint
@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """Simple test WebSocket endpoint"""
    await websocket.accept()
    await websocket.send_text("Hello WebSocket!")
    await websocket.close()


@app.get("/", tags=["root"])
async def read_root():
    return {"message": "Welcome to the Messaging App API!"}


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "message": "API is running smoothly!"}


@app.get("/version", tags=["version"])
async def get_version():
    return {"version": "1.0.0", "description": "Messaging App API Version 1.0.0"}
