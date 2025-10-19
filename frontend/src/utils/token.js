import jwtDecode from 'jwt-decode';

/**
 * Token Utility
 * Handles JWT token storage, retrieval, and validation
 */

const TOKEN_KEY = 'access_token';
const USER_KEY = 'user';

export const setToken = (token) => {
  try {
    if (!token) {
      throw new Error('Token is required');
    }
    localStorage.setItem(TOKEN_KEY, token);
  } catch (error) {
    console.error('Error setting token:', error);
    throw error;
  }
};

export const getToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch (error) {
    console.error('Error getting token:', error);
    return null;
  }
};

export const removeToken = () => {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch (error) {
    console.error('Error removing token:', error);
  }
};

export const decodeToken = (token = null) => {
  try {
    const tokenToDecode = token || getToken();
    if (!tokenToDecode) {
      return null;
    }

    const decoded = jwtDecode(tokenToDecode);
    return decoded;
  } catch (error) {
    console.error('Error decoding token:', error);
    return null;
  }
};

export const isTokenExpired = (token = null) => {
  try {
    const decoded = decodeToken(token);
    if (!decoded || !decoded.exp) {
      return true;
    }
    // JWT exp is in seconds, Date.now() is in milliseconds
    const currentTime = Date.now() / 1000;
    // Add 10 second buffer to account for clock skew
    return decoded.exp < currentTime + 10;
  } catch (error) {
    console.error('Error checking token expiration:', error);
    return true;
  }
};

export const isAuthenticated = () => {
  const token = getToken();
  if (!token) {
    return false;
  }

  return !isTokenExpired(token);
};

export const getUserFromToken = (token = null) => {
  try {
    const decoded = decodeToken(token);
    if (!decoded) {
      return null;
    }
    // Extract user information from token payload
    // Adjust based on your backend JWT structure
    return {
      userId: decoded.sub,
      email: decoded.email,
      username: decoded.username,
      displayName: decoded.display_name,
      exp: decoded.exp,
    };
  } catch (error) {
    console.error('Error extracting user from token:', error);
    return null;
  }
};

export const getTokenExpiration = (token = null) => {
  try {
    const decoded = decodeToken(token);
    if (!decoded || !decoded.exp) {
      return null;
    }
    // Convert exp from seconds to milliseconds
    return new Date(decoded.exp * 1000);
  } catch (error) {
    console.error('Error getting token expiration:', error);
    return null;
  }
};

export const getTokenRemainingTime = (token = null) => {
  try {
    const decoded = decodeToken(token);
    if (!decoded || !decoded.exp) {
      return 0;
    }

    const currentTime = Date.now() / 1000; // in seconds
    const remainingTime = decoded.exp - currentTime;

    return remainingTime > 0 ? Math.floor(remainingTime) : 0;
  } catch (error) {
    console.error('Error getting token remaining time:', error);
    return 0;
  }
};

// Default export with all utility functions
const tokenUtils = {
  setToken,
  getToken,
  removeToken,
  decodeToken,
  isTokenExpired,
  isAuthenticated,
  getUserFromToken,
  getTokenExpiration,
  getTokenRemainingTime,
};

export default tokenUtils;
