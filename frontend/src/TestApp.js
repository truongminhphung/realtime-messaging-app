import React, { useState } from 'react';
import ChatRoom from './components/ChatRoom';
import './TestApp.css';

const TestApp = () => {
  const [token, setToken] = useState(localStorage.getItem('auth_token') || '');
  const [roomId, setRoomId] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('auth_token'));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          username,
          password,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const authToken = data.access_token;
        
        setToken(authToken);
        localStorage.setItem('auth_token', authToken);
        setIsLoggedIn(true);
        setError('');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Login failed');
      }
    } catch (err) {
      setError('Network error: Unable to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setToken('');
    setRoomId('');
    localStorage.removeItem('auth_token');
    setIsLoggedIn(false);
  };

  const handleJoinRoom = (e) => {
    e.preventDefault();
    if (!roomId.trim()) {
      setError('Please enter a room ID');
      return;
    }
    setError('');
  };

  if (!isLoggedIn) {
    return (
      <div className="test-app">
        <div className="auth-container">
          <h1>Realtime Messaging App - Test</h1>
          <form onSubmit={handleLogin} className="auth-form">
            <h2>Login</h2>
            {error && <div className="error-message">{error}</div>}
            
            <div className="form-group">
              <label htmlFor="username">Username:</label>
              <input
                type="text"
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="password">Password:</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            
            <button type="submit" disabled={loading} className="auth-button">
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
          
          <div className="test-info">
            <h3>Test Instructions:</h3>
            <ol>
              <li>Make sure the backend server is running on localhost:8000</li>
              <li>Create a user account using the API or use an existing one</li>
              <li>Login with your credentials</li>
              <li>Enter a room UUID to join the chat</li>
              <li>Open multiple browser tabs to test real-time messaging</li>
            </ol>
            
            <h4>Sample API calls to create test data:</h4>
            <pre>
{`# Create a user
curl -X POST "http://localhost:8000/auth/register" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "testuser", "email": "test@example.com", "password": "testpass123"}'

# Create a room
curl -X POST "http://localhost:8000/rooms" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "Test Room", "description": "A test chat room"}'`}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  if (!roomId) {
    return (
      <div className="test-app">
        <div className="room-selector">
          <div className="header-with-logout">
            <h1>Select Chat Room</h1>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
          
          <form onSubmit={handleJoinRoom} className="room-form">
            {error && <div className="error-message">{error}</div>}
            
            <div className="form-group">
              <label htmlFor="roomId">Room ID (UUID):</label>
              <input
                type="text"
                id="roomId"
                value={roomId}
                onChange={(e) => setRoomId(e.target.value)}
                placeholder="e.g., 550e8400-e29b-41d4-a716-446655440000"
                required
              />
            </div>
            
            <button type="submit" className="join-button">
              Join Room
            </button>
          </form>
          
          <div className="room-info">
            <h3>How to get a Room ID:</h3>
            <ol>
              <li>Create a room using the API:</li>
              <pre>
{`curl -X POST "http://localhost:8000/rooms" \\
  -H "Authorization: Bearer ${token.slice(0, 20)}..." \\
  -H "Content-Type: application/json" \\
  -d '{"name": "My Test Room", "description": "Test room for WebSocket"}'`}
              </pre>
              <li>Copy the room_id from the response</li>
              <li>Make sure you're a participant in the room</li>
            </ol>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="test-app">
      <div className="chat-header-controls">
        <button onClick={() => setRoomId('')} className="back-button">
          ← Back to Room Selection
        </button>
        <button onClick={handleLogout} className="logout-button">
          Logout
        </button>
      </div>
      <ChatRoom roomId={roomId} token={token} />
    </div>
  );
};

export default TestApp;
