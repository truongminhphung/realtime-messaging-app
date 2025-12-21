import React from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      {/* Navigation Header */}
      <header className="landing-header">
        <div className="logo">
          <span className="logo-icon">💬</span>
          <span className="logo-text">ChatConnect</span>
        </div>
        <nav className="nav-links">
          <button onClick={() => navigate('/login')} className="nav-btn login-btn">
            Login
          </button>
          <button onClick={() => navigate('/signup')} className="nav-btn signup-btn">
            Sign Up
          </button>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            Connect Instantly,
            <br />
            <span className="hero-gradient">Chat Effortlessly</span>
          </h1>
          <p className="hero-description">
            Experience real-time messaging with a modern, intuitive interface.
            Connect with friends, family, and colleagues instantly.
          </p>
          <div className="hero-buttons">
            <button onClick={() => navigate('/signup')} className="btn btn-primary">
              Get Started Free
            </button>
            <button onClick={() => navigate('/login')} className="btn btn-secondary">
              Sign In
            </button>
          </div>
        </div>
        <div className="hero-visual">
          <div className="chat-bubble bubble-1">
            <div className="bubble-avatar">👋</div>
            <div className="bubble-text">Hey there!</div>
          </div>
          <div className="chat-bubble bubble-2">
            <div className="bubble-avatar">😊</div>
            <div className="bubble-text">Welcome to ChatConnect!</div>
          </div>
          <div className="chat-bubble bubble-3">
            <div className="bubble-avatar">🚀</div>
            <div className="bubble-text">Let&apos;s get started</div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2 className="section-title">Why Choose ChatConnect?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3 className="feature-title">Real-Time Messaging</h3>
            <p className="feature-description">
              Instant message delivery with WebSocket technology for seamless communication.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3 className="feature-title">Secure & Private</h3>
            <p className="feature-description">
              End-to-end encryption ensures your conversations remain private and secure.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🌐</div>
            <h3 className="feature-title">Cross-Platform</h3>
            <p className="feature-description">
              Access your messages anywhere, anytime on any device with a browser.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">👥</div>
            <h3 className="feature-title">Group Chats</h3>
            <p className="feature-description">
              Create rooms and connect with multiple people in organized conversations.
            </p>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="contact-section">
        <h2 className="section-title">Get In Touch</h2>
        <p className="contact-description">
          Have questions? We&apos;re here to help you get started.
        </p>
        <div className="contact-info">
          <div className="contact-item">
            <div className="contact-icon">📧</div>
            <div className="contact-details">
              <h4>Email</h4>
              <a href="mailto:support@chatconnect.com">support@chatconnect.com</a>
            </div>
          </div>
          <div className="contact-item">
            <div className="contact-icon">💬</div>
            <div className="contact-details">
              <h4>Live Chat</h4>
              <p>Available 24/7 for support</p>
            </div>
          </div>
          <div className="contact-item">
            <div className="contact-icon">🌍</div>
            <div className="contact-details">
              <h4>Location</h4>
              <p>Ho Chi Minh City, Vietnam</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-section">
            <h4>ChatConnect</h4>
            <p>Real-time messaging made simple</p>
          </div>
          <div className="footer-section">
            <h4>Quick Links</h4>
            <ul>
              <li><button onClick={() => navigate('/login')}>Login</button></li>
              <li><button onClick={() => navigate('/signup')}>Sign Up</button></li>
              <li><button onClick={() => navigate('/forgot-password')}>Reset Password</button></li>
            </ul>
          </div>
          <div className="footer-section">
            <h4>Legal</h4>
            <ul>
              <li><a href="#privacy">Privacy Policy</a></li>
              <li><a href="#terms">Terms of Service</a></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2025 ChatConnect. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
