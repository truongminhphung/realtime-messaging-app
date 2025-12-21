import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import './Auth.css';

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [validationError, setValidationError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setEmail(e.target.value);
    if (validationError) {
      setValidationError('');
    }
    if (error) {
      setError('');
    }
  };

  const validateEmail = () => {
    if (!email.trim()) {
      setValidationError('Email is required');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setValidationError('Please enter a valid email address');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSuccessMessage('');
    setError('');

    if (!validateEmail()) {
      return;
    }

    setIsLoading(true);

    try {
      // Note: This is a placeholder implementation
      // In a real application, you would call your backend API here
      // For example: await api.post('/auth/forgot-password', { email });

      // Simulating API call
      await new Promise(resolve => setTimeout(resolve, 1500));

      setSuccessMessage(
        'If an account exists with this email, you will receive password reset instructions shortly.'
      );

      // Clear form
      setEmail('');

      // Redirect to login after 4 seconds
      setTimeout(() => {
        navigate('/login');
      }, 4000);
    } catch (err) {
      console.error('Forgot password error:', err);
      setError('Something went wrong. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <button onClick={() => navigate('/')} className="back-button">
            ← Back to Home
          </button>
        </div>

        <div className="auth-card">
          <div className="auth-logo">
            <span className="auth-logo-icon">💬</span>
            <h1>ChatConnect</h1>
          </div>

          <h2 className="auth-title">Reset Password</h2>
          <p className="auth-subtitle">
            Enter your email address and we&apos;ll send you instructions to reset your password
          </p>

          {error && (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}

          {successMessage && (
            <div className="success-message">
              <span className="success-icon">✅</span>
              {successMessage}
            </div>
          )}

          {!successMessage && (
            <form onSubmit={handleSubmit} className="auth-form">
              <div className="form-group">
                <label htmlFor="email">Email Address</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={email}
                  onChange={handleChange}
                  placeholder="Enter your email"
                  className={validationError ? 'input-error' : ''}
                  autoComplete="email"
                />
                {validationError && (
                  <span className="field-error">{validationError}</span>
                )}
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={isLoading}
              >
                {isLoading ? 'Sending instructions...' : 'Send Reset Instructions'}
              </button>
            </form>
          )}

          <div className="auth-divider">
            <span>or</span>
          </div>

          <p className="auth-switch">
            Remember your password?{' '}
            <Link to="/login" className="auth-link">
              Sign in
            </Link>
          </p>

          <p className="auth-switch">
            Don&apos;t have an account?{' '}
            <Link to="/signup" className="auth-link">
              Sign up now
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
