import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, AuthContext } from './AuthContext';
import authService from '../services/authService';
import * as tokenUtils from '../utils/token';

// Mock dependencies
jest.mock('../services/authService');
jest.mock('../utils/token');

describe('AuthContext', () => {
  // Mock console methods
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    console.error.mockRestore();
    console.log.mockRestore();
  });

  const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;

  describe('checkAuth', () => {
    it('should set authenticated when valid token exists', async () => {
      const mockToken = 'valid-token';
      const mockUser = {
        userId: 'user-123',
        email: 'test@example.com',
        username: 'testuser',
        displayName: 'Test User',
      };

      tokenUtils.getToken.mockReturnValue(mockToken);
      tokenUtils.isTokenExpired.mockReturnValue(false);
      tokenUtils.getUserFromToken.mockReturnValue(mockUser);

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockUser);
    });

    it('should set not authenticated when no token exists', async () => {
      tokenUtils.getToken.mockReturnValue(null);

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('should clear auth when token is expired', async () => {
      tokenUtils.getToken.mockReturnValue('expired-token');
      tokenUtils.isTokenExpired.mockReturnValue(true);
      tokenUtils.removeToken.mockImplementation(() => {});

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(tokenUtils.removeToken).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('should handle verification error gracefully', async () => {
      const mockUser = {
        userId: 'user-123',
        email: 'test@example.com',
        username: 'testuser',
      };

      tokenUtils.getToken.mockReturnValue('token');
      tokenUtils.isTokenExpired.mockReturnValue(false);
      tokenUtils.getUserFromToken.mockImplementation(() => {
        throw new Error('Invalid token format');
      });
      tokenUtils.removeToken.mockImplementation(() => {});

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(tokenUtils.removeToken).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('login', () => {
    it('should login user successfully', async () => {
      const mockResponse = {
        access_token: 'new-token',
        user: {
          user_id: 'user-123',
          email: 'test@example.com',
          username: 'testuser',
          display_name: 'Test User',
        },
      };

      const mockUser = {
        userId: 'user-123',
        email: 'test@example.com',
        username: 'testuser',
        displayName: 'Test User',
      };

      authService.login.mockResolvedValue(mockResponse);
      tokenUtils.getUserFromToken.mockReturnValue(mockUser);

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      // Wait for initial checkAuth to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let loginResult;
      await act(async () => {
        loginResult = await result.current.login('test@example.com', 'password123');
      });

      expect(authService.login).toHaveBeenCalledWith('test@example.com', 'password123');
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user.email).toBe('test@example.com');
      expect(loginResult).toEqual(mockResponse);
    });

    it('should handle login error', async () => {
      const error = { detail: 'Incorrect email or password' };
      authService.login.mockRejectedValue(error);

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let caughtError;
      await act(async () => {
        try {
          await result.current.login('wrong@email.com', 'wrongpass');
        } catch (err) {
          caughtError = err;
        }
      });

      expect(caughtError).toEqual(error);
      expect(result.current.error).toBe('Incorrect email or password');
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('register', () => {
    it('should register user successfully', async () => {
      const userData = {
        email: 'new@example.com',
        username: 'newuser',
        password: 'Password123',
      };

      const mockResponse = {
        message: 'User registered successfully',
        user: {
          user_id: 'new-user-id',
          email: 'new@example.com',
          username: 'newuser',
        },
      };

      authService.register.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let registerResult;
      await act(async () => {
        registerResult = await result.current.register(userData);
      });

      expect(authService.register).toHaveBeenCalledWith(userData);
      expect(registerResult).toEqual(mockResponse);
    });

    it('should handle registration error', async () => {
      const error = { detail: 'Email already exists' };
      authService.register.mockRejectedValue(error);

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let caughtError;
      await act(async () => {
        try {
          await result.current.register({ email: 'existing@example.com' });
        } catch (err) {
          caughtError = err;
        }
      });

      expect(caughtError).toEqual(error);
      expect(result.current.error).toBe('Email already exists');
    });
  });

  describe('logout', () => {
    it('should logout user successfully', async () => {
      const mockToken = 'token';
      tokenUtils.getToken.mockReturnValue(mockToken);
      authService.logout.mockResolvedValue({ message: 'Logged out' });
      tokenUtils.removeToken.mockImplementation(() => {});

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(authService.logout).toHaveBeenCalledWith(mockToken);
      expect(tokenUtils.removeToken).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('should clear client data even if backend logout fails', async () => {
      const mockToken = 'token';
      tokenUtils.getToken.mockReturnValue(mockToken);
      authService.logout.mockRejectedValue(new Error('Backend error'));
      tokenUtils.removeToken.mockImplementation(() => {});

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      let caughtError;
      await act(async () => {
        try {
          await result.current.logout();
        } catch (err) {
          caughtError = err;
        }
      });

      expect(caughtError).toBeDefined();
      expect(tokenUtils.removeToken).toHaveBeenCalled();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear error message', async () => {
      authService.login.mockRejectedValue({ detail: 'Error message' });

      const { result } = renderHook(() => React.useContext(AuthContext), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Cause an error
      await act(async () => {
        try {
          await result.current.login('test@test.com', 'wrong');
        } catch (err) {
          // Error expected
        }
      });

      await waitFor(() => {
        expect(result.current.error).toBe('Error message');
      });

      // Clear error
      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });
});