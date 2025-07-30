from contextlib import asynccontextmanager

from fastapi import FastAPI

from realtime_messaging.routes import auth, users, messages, rooms, notifications
from realtime_messaging.websocket import chat
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
app.include_router(messages.router)
app.include_router(rooms.router)
app.include_router(notifications.router)
app.include_router(chat.router)


@app.get("/", tags=["root"])
async def read_root():
    return {"message": "Welcome to the Messaging App API!"}


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "message": "API is running smoothly!"}


@app.get("/version", tags=["version"])
async def get_version():
    return {"version": "1.0.0", "description": "Messaging App API Version 1.0.0"}
