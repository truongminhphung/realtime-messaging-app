import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import ChatRoom from './components/ChatRoom';
import './App.css';

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <ChatRoom />
      </AuthProvider>
    </div>
  );
}

export default App;