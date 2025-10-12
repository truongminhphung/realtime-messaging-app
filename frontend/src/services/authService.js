import api from './api';
import { setToken, removeToken } from '../utils/token';

/**
 * Authentication Service
 * Handles all authentication-related API calls
 */
const authService = {
  /**
   * Register a new user
   * @param {Object} userData - User registration data
   * @param {string} userData.email - User's email address
   * @param {string} userData.username - Username (3-20 chars, alphanumeric + underscore/hyphen)
   * @param {string} userData.password - Password (8+ chars, 1 uppercase, 1 lowercase, 1 digit)
   * @param {string} [userData.display_name] - Optional display name
   * @returns {Promise<Object>} Response with user data
   */
  async register(userData) {
    try {
      const response = await api.post('/auth/register', userData);
      return response.data;
    } catch (error) {
      throw this._handleError(error);
    }
  },
  /**
   * Login user with email and password
   * @param {string} email - User's email address
   * @param {string} password - User's password
   * @returns {Promise<Object>} Response with access token and user data
   */
  async login(email, password) {
    try {
      const response = await api.post('/auth/login', { email, password });
      // Store token and user info in localStorage if login is successful
      if (response.data.access_token) {
        setToken(response.data.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
      }
      return response.data;
    } catch (error) {
      throw this._handleError(error);
    }
  },

  /**
   * Logout the current user
   * @returns {Promise<Object>} Response message
   */
  async logout() {
    try {
      const token = localStorage.getItem('access_token');
      if (token) {
        await api.post(
          '/auth/logout',
          {},
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        // Clear local storage
        removeToken();

        return { message: 'Logged out successfully' };
      }
    } catch (error) {
      // Still clear local storage even if logout API fails
      removeToken();
      throw this._handleError(error);
    }
  },
  /**
   * Get the currently authenticated user's profile
   * @returns {Promise<Object>} User data
   */
  async getCurrentUser() {
    try {
      const response = await api.get('/auth/me');
      return response.data;
    } catch (error) {
      throw this._handleError(error);
    }
  },
  /**
   * Check if the user is authenticated
   * @returns {boolean} True if authenticated, false otherwise
   */
  isAuthenticated() {
    const token = localStorage.getItem('access_token');
    return !!token;
  },
  /**
   * Get stored user data from localStorage
   * @returns {Object|null} User data or null if not found
   */
  getStoredUser() {
    try {
      const user = localStorage.getItem('user');
      return user ? JSON.parse(user) : null;
    } catch (error) {
      console.error('Error getting stored user:', error);
      return null;
    }
  },
  /**
   * Get the stored access token from localStorage
   * @returns {string|null} Access token or null if not found
   */
  getToken() {
    return localStorage.getItem('access_token');
  },

  /**
   * Handle API errors and return user-friendly messages
   * @private
   * @param {Error} error - Error object from API call
   * @returns {Error} Formatted error
   */
  _handleError(error) {
    if (error.response) {
      // Server responded with a status other than 2xx
      const status = error.response.status;
      const message =
        error.response.data?.detail || error.response.data?.message;

      switch (status) {
        case 400:
          return new Error(
            message || 'Invalid request. Please check your input.'
          );
        case 401:
          return new Error(message || 'Incorrect email or password.');
        case 403:
          return new Error(
            message || 'You do not have permission to perform this action.'
          );
        case 404:
          return new Error(message || 'User not found.');
        case 500:
          return new Error(message || 'Server error. Please try again later.');
        default:
          return new Error(
            message || `Unexpected error occurred (status code: ${status}).`
          );
      }
    } else if (error.request) {
      // Request was made but no response received
      return new Error('Network error: Please check your internet connection.');
    } else {
      // Something else happened while setting up the request
      return new Error(error.message || 'An unexpected error occurred.');
    }
  },
};

export default authService;
