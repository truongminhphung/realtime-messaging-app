# guide to test notification system
# Terminal 1: Start the main API server
cd backend
source env.sh
uv run uvicorn realtime_messaging.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start the notification worker
cd /home/phung/Documents/my_project/realtime-messaging-app/backend
export PYTHONPATH=/home/phung/Documents/my_project/realtime-messaging-app/backend:$PYTHONPATH
source env.sh
uv run python realtime_messaging/workers/notification_worker.py

# Terminal 3: Test the invitation flow
# Login to get token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "phung111@gmail.com", "password": "Phung111"}' \
  | jq -r '.access_token')

# Invite a user to a room
curl -X POST "http://localhost:8000/rooms/{room_id}/invite" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invitee_email": "friend@example.com"}'