import React, { useState, useEffect, useRef } from 'react';
import './ChatRoom.css';

const ChatRoom = ({ roomId, token }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState(0);
  const [typingUsers, setTypingUsers] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);
  const [rateLimitInfo, setRateLimitInfo] = useState(null);
  
  const ws = useRef(null);
  const messagesEndRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  useEffect(() => {
    if (!roomId || !token) return;

    // Create WebSocket connection
    const wsUrl = `ws://localhost:8000/ws/${roomId}?token=${token}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setError(null);
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected', event.code, event.reason);
      setIsConnected(false);
      if (event.code === 1008) {
        setError(`Connection closed: ${event.reason}`);
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('WebSocket connection error');
    };

    // Cleanup on unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [roomId, token]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'connected':
        setOnlineUsers(data.data.connected_users);
        break;
      
      case 'new_message':
        setMessages(prev => [...prev, data.data]);
        break;
      
      case 'message_sent':
        // Message was successfully sent
        break;
      
      case 'message_error':
        setError(data.data.error);
        break;
      
      case 'rate_limit_exceeded':
        setError(data.data.error);
        setRateLimitInfo(data.data.rate_limit_info);
        break;
      
      case 'user_joined':
        setOnlineUsers(prev => prev + 1);
        addSystemMessage(`${data.data.display_name} joined the room`);
        break;
      
      case 'user_left':
        setOnlineUsers(prev => Math.max(0, prev - 1));
        addSystemMessage(`${data.data.display_name} left the room`);
        break;
      
      case 'user_typing':
        setTypingUsers(prev => {
          if (!prev.includes(data.data.display_name)) {
            return [...prev, data.data.display_name];
          }
          return prev;
        });
        break;
      
      case 'user_stopped_typing':
        setTypingUsers(prev => prev.filter(name => name !== data.data.display_name));
        break;
      
      case 'pong':
        // Handle ping response
        break;
      
      case 'error':
        setError(data.data.error);
        break;
      
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const addSystemMessage = (content) => {
    const systemMessage = {
      message_id: Date.now().toString(),
      content,
      created_at: new Date().toISOString(),
      sender: {
        display_name: 'System',
        username: 'system'
      },
      is_system: true
    };
    setMessages(prev => [...prev, systemMessage]);
  };

  const sendMessage = () => {
    if (!newMessage.trim() || !isConnected) return;

    const message = {
      type: 'send_message',
      data: {
        content: newMessage.trim()
      }
    };

    ws.current.send(JSON.stringify(message));
    setNewMessage('');
    stopTyping();
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    } else {
      handleTyping();
    }
  };

  const handleTyping = () => {
    if (!isTyping && isConnected) {
      setIsTyping(true);
      ws.current.send(JSON.stringify({
        type: 'typing_start',
        data: {}
      }));
    }

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout to stop typing
    typingTimeoutRef.current = setTimeout(() => {
      stopTyping();
    }, 3000);
  };

  const stopTyping = () => {
    if (isTyping && isConnected) {
      setIsTyping(false);
      ws.current.send(JSON.stringify({
        type: 'typing_stop',
        data: {}
      }));
    }
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const clearError = () => {
    setError(null);
    setRateLimitInfo(null);
  };

  return (
    <div className="chat-room">
      <div className="chat-header">
        <h2>Room: {roomId}</h2>
        <div className="status">
          <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
          <span className="online-users">
            👥 {onlineUsers} online
          </span>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          {rateLimitInfo && (
            <div className="rate-limit-info">
              <small>
                Messages sent: {rateLimitInfo.messages_sent}/{rateLimitInfo.max_messages} 
                (resets in {Math.ceil(rateLimitInfo.time_until_reset / 60)} minutes)
              </small>
            </div>
          )}
          <button onClick={clearError} className="close-error">×</button>
        </div>
      )}

      <div className="messages-container">
        {messages.map((message) => (
          <div 
            key={message.message_id} 
            className={`message ${message.is_system ? 'system-message' : ''}`}
          >
            <div className="message-header">
              <span className="sender-name">
                {message.sender.display_name || message.sender.username}
              </span>
              <span className="timestamp">
                {formatTimestamp(message.created_at)}
              </span>
            </div>
            <div className="message-content">
              {message.content}
            </div>
          </div>
        ))}
        {typingUsers.length > 0 && (
          <div className="typing-indicator">
            <em>{typingUsers.join(', ')} {typingUsers.length === 1 ? 'is' : 'are'} typing...</em>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="message-input-container">
        <textarea
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={!isConnected}
          rows="2"
          className="message-input"
        />
        <button 
          onClick={sendMessage}
          disabled={!isConnected || !newMessage.trim()}
          className="send-button"
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatRoom;
