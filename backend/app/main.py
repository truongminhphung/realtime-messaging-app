from fastapi import FastAPI
from app.routes import auth, users, messages, rooms, notifications
from app.websocket import chat

app = FastAPI()
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.websocket("/ws/{room_id}", name="websocket_chat")(chat.websocket_endpoint)

@app.get("/", tags=["root"])
async def read_root():
    return {"message": "Welcome to the Messaging App API!"}
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "message": "API is running smoothly!"}
@app.get("/version", tags=["version"])
async def get_version():
    return {"version": "1.0.0", "description": "Messaging App API Version 1.0.0"}

@app.on_event("startup")
async def startup_event():
    # Initialize any resources needed at startup, like database connections
    print("Starting up the Messaging App API...")
@app.on_event("shutdown")
async def shutdown_event():
    # Clean up resources, close database connections, etc.
    print("Shutting down the Messaging App API...")