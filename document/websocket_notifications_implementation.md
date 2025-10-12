# WebSocket Notifications Implementation

## Overview

The realtime messaging app now supports instant notifications via WebSocket connections. This enables real-time delivery of notifications without requiring users to refresh their page or poll the server.

## Architecture

### Backend Components

1. **NotificationWorker** (`workers/notification_worker.py`)
   - Processes notifications from RabbitMQ queues
   - Sends emails via SMTP
   - Delivers real-time notifications via WebSocket
   - Updates notification status in database

2. **NotificationManager** (`websocket/notification_manager.py`)
   - Manages WebSocket connections per user
   - Broadcasts notifications to connected clients
   - Handles connection cleanup and error recovery

3. **WebSocket Endpoints** (`websocket/notification_endpoints.py`)
   - Authenticated WebSocket endpoint at `/ws/notifications`
   - Supports ping/pong for connection health
   - Handles message type routing (ping, get_unread_count, mark_read)

### Authentication

WebSocket connections are authenticated using JWT tokens passed as query parameters:
```
ws://localhost:8000/ws/notifications?token=your_jwt_token
```

## Frontend Integration

### JavaScript WebSocket Client

```javascript
class NotificationClient {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl.replace('http', 'ws');
        this.token = token;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 1000; // 1 second
    }

    connect() {
        const wsUrl = `${this.baseUrl}/ws/notifications?token=${this.token}`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = (event) => {
                console.log('WebSocket connected for notifications');
                this.reconnectAttempts = 0;
                
                // Request current unread count
                this.send({ type: 'get_unread_count' });
                
                // Start heartbeat
                this.startHeartbeat();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    // Handle legacy text messages
                    if (event.data === 'pong') {
                        console.log('Received heartbeat pong');
                    }
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.stopHeartbeat();
                
                if (event.code !== 1000) { // Not a normal closure
                    this.attemptReconnect();
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.attemptReconnect();
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'notification':
                this.onNotification(data.data);
                break;
            case 'unread_count':
                this.onUnreadCount(data.data.count);
                break;
            case 'notification_update':
                this.onNotificationUpdate(data.data);
                break;
            case 'pong':
                console.log('Received heartbeat pong');
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    onNotification(notification) {
        // Display notification to user
        console.log('New notification:', notification);
        
        // Show browser notification if permission granted
        if (Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: '/favicon.ico',
                tag: notification.notification_id
            });
        }
        
        // Update UI (e.g., notification badge, list)
        this.updateNotificationUI(notification);
        
        // Play notification sound
        this.playNotificationSound();
    }

    onUnreadCount(count) {
        // Update unread count badge in UI
        console.log(`Unread notifications: ${count}`);
        this.updateUnreadBadge(count);
    }

    onNotificationUpdate(update) {
        // Handle notification status changes (read, delivered, etc.)
        console.log('Notification update:', update);
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    markNotificationAsRead(notificationId) {
        this.send({
            type: 'mark_read',
            notification_id: notificationId
        });
    }

    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.send({ type: 'ping' });
            }
        }, 30000); // Ping every 30 seconds
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectInterval * this.reconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    updateNotificationUI(notification) {
        // Implementation depends on your UI framework
        // This is where you'd update React state, Vue data, etc.
    }

    updateUnreadBadge(count) {
        // Update notification badge in header/navbar
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = count > 0 ? count : '';
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    playNotificationSound() {
        // Play subtle notification sound
        const audio = new Audio('/notification.mp3');
        audio.volume = 0.3;
        audio.play().catch(e => console.log('Could not play notification sound'));
    }

    disconnect() {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close(1000, 'Client disconnecting');
            this.ws = null;
        }
    }
}

// Usage example
const token = localStorage.getItem('jwt_token'); // Get from your auth system
const notificationClient = new NotificationClient('ws://localhost:8000', token);

// Connect when user logs in
notificationClient.connect();

// Disconnect when user logs out
window.addEventListener('beforeunload', () => {
    notificationClient.disconnect();
});
```

### React Hook Example

```javascript
import { useState, useEffect, useRef } from 'react';

export function useNotifications(token) {
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [connected, setConnected] = useState(false);
    const clientRef = useRef(null);

    useEffect(() => {
        if (!token) return;

        const client = new NotificationClient('ws://localhost:8000', token);
        
        // Override client methods to update React state
        const originalOnNotification = client.onNotification.bind(client);
        client.onNotification = (notification) => {
            originalOnNotification(notification);
            setNotifications(prev => [notification, ...prev]);
            setUnreadCount(prev => prev + 1);
        };

        const originalOnUnreadCount = client.onUnreadCount.bind(client);
        client.onUnreadCount = (count) => {
            originalOnUnreadCount(count);
            setUnreadCount(count);
        };

        client.ws.onopen = () => setConnected(true);
        client.ws.onclose = () => setConnected(false);

        client.connect();
        clientRef.current = client;

        return () => {
            client.disconnect();
        };
    }, [token]);

    const markAsRead = (notificationId) => {
        if (clientRef.current) {
            clientRef.current.markNotificationAsRead(notificationId);
            setUnreadCount(prev => Math.max(0, prev - 1));
        }
    };

    return {
        notifications,
        unreadCount,
        connected,
        markAsRead
    };
}
```

## Message Types

### Client to Server

1. **ping**: Health check
   ```json
   { "type": "ping" }
   ```

2. **get_unread_count**: Request current unread count
   ```json
   { "type": "get_unread_count" }
   ```

3. **mark_read**: Mark notification as read
   ```json
   { 
     "type": "mark_read", 
     "notification_id": "uuid-string" 
   }
   ```

### Server to Client

1. **pong**: Health check response
   ```json
   { "type": "pong" }
   ```

2. **notification**: New notification
   ```json
   {
     "type": "notification",
     "data": {
       "title": "New message from John",
       "message": "John: Hello there...",
       "notification_type": "new_message",
       "timestamp": "2024-01-15T10:30:00Z",
       "room_id": "room-uuid",
       "sender_id": "user-uuid"
     }
   }
   ```

3. **unread_count**: Current unread count
   ```json
   {
     "type": "unread_count",
     "data": {
       "count": 5
     }
   }
   ```

4. **notification_update**: Status change
   ```json
   {
     "type": "notification_update",
     "data": {
       "notification_id": "uuid-string",
       "status": "read"
     }
   }
   ```

## Deployment Considerations

### Load Balancing

When deploying behind a load balancer:

1. Enable sticky sessions for WebSocket connections
2. Or use Redis for shared WebSocket connection state
3. Consider using a dedicated WebSocket server (Socket.IO with Redis adapter)

### Scaling

For high-traffic scenarios:

1. **Horizontal Scaling**: Multiple worker processes with Redis pub/sub
2. **Connection Pooling**: Limit connections per user/server
3. **Message Queuing**: Use RabbitMQ for reliable notification delivery
4. **Database Optimization**: Index notification tables properly

### Monitoring

Key metrics to monitor:

- Active WebSocket connections
- Notification delivery success rate
- Average notification latency
- RabbitMQ queue depths
- Database performance for notification queries

## Security

1. **Authentication**: JWT tokens with proper expiration
2. **Rate Limiting**: Prevent WebSocket spam
3. **Input Validation**: Sanitize all incoming messages
4. **CORS**: Configure properly for WebSocket origins
5. **SSL/TLS**: Use WSS in production

## Testing

### Manual Testing

```bash
# Install wscat for testing
npm install -g wscat

# Connect to WebSocket (replace with your token)
wscat -c "ws://localhost:8000/ws/notifications?token=your_jwt_token"

# Send test messages
> {"type": "ping"}
< {"type": "pong"}

> {"type": "get_unread_count"}
< {"type": "unread_count", "data": {"count": 0}}
```

### Automated Testing

Unit tests should cover:
- Authentication validation
- Message handling
- Connection management
- Error scenarios
- Reconnection logic