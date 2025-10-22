import React, { createContext, useState, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import authService from '../services/authService';
import {
  getToken,
  removeToken,
  isTokenExpired,
  getUserFromToken,
} from '../utils/token';

// Create the AuthContext
export const AuthContext = createContext(null);

// AuthProvider component to wrap around the app
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkAuth = useCallback(async () => {
    try {
      setIsLoading(true);
      const token = getToken();

      // no token found
      if (!token) {
        setIsAuthenticated(false);
        setUser(null);
        setIsLoading(false);
        return;
      }

      // token found but expired
      if (isTokenExpired(token)) {
        console.log('Token expired');
        setIsAuthenticated(false);
        setUser(null);
        removeToken();
        setIsLoading(false);
        return;
      }

      // Token exists and is valid
      const user = getUserFromToken(token);
      setUser(user);
      setIsAuthenticated(true);
    } catch (err) {
      console.error('Error during authentication check:', err);
      setIsAuthenticated(false);
      setUser(null);
      removeToken();
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await authService.login(email, password);

      const userData = getUserFromToken(response.data.access_token);
      setUser(userData);
      setIsAuthenticated(true);

      return response;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await authService.register(userData);
      return response;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      setIsLoading(true);
      setError(null);

      await authService.logout();
      setUser(null);
      setIsAuthenticated(false);
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };
  // Check authentication on mount
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Context value
  const value = {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Add PropTypes validation
AuthProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export default AuthProvider;
