import jwtDecode from 'jwt-decode';
import {
  setToken,
  getToken,
  removeToken,
  decodeToken,
  isTokenExpired,
  isAuthenticated,
  getUserFromToken,
  getTokenExpiration,
  getTokenRemainingTime,
} from './token';

// MOCK EXTERNAL DEPENDENCIES
// Mock jwt-decode module
jest.mock('jwt-decode', () => jest.fn());

// MAIN TEST SUITE
describe('Token Utility Functions', () => {
  // Store original localStorage
  const originalLocalStorage = global.localStorage;

  // Runs before EACH test
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    
    // Create a mock localStorage with actual implementation
    const store = {};
    const localStorageMock = {
      getItem: jest.fn((key) => store[key] || null),
      setItem: jest.fn((key, value) => {
        store[key] = value.toString();
      }),
      removeItem: jest.fn((key) => {
        delete store[key];
      }),
      clear: jest.fn(() => {
        Object.keys(store).forEach(key => delete store[key]);
      }),
    };
    
    // Replace global localStorage
    Object.defineProperty(global, 'localStorage', {
      value: localStorageMock,
      writable: true,
      configurable: true,
    });
    
    // Mock console methods to avoid noise in test output
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  // Runs after EACH test
  afterEach(() => {
    // Restore mocked functions
    console.error.mockRestore();
    
    // Restore original localStorage
    Object.defineProperty(global, 'localStorage', {
      value: originalLocalStorage,
      writable: true,
      configurable: true,
    });
  });

  describe('setToken', () => {
    it('should store token in localStorage', () => {
      const token = 'test-token-123';
      
      setToken(token);
      
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', token);
    });

    it('should throw error when token is null', () => {
      expect(() => setToken(null)).toThrow('Token is required');
    });

    it('should throw error when token is undefined', () => {
      expect(() => setToken(undefined)).toThrow('Token is required');
    });

    it('should throw error when token is empty string', () => {
      expect(() => setToken('')).toThrow('Token is required');
    });
    
    // mockImplementation() - Override what the mock does => Here we make it throw an error
    it('should handle localStorage errors', () => {
      const error = new Error('Storage quota exceeded');
      // Make localStorage.setItem throw an error
      localStorage.setItem.mockImplementation(() => {
        throw error;
      });

      expect(() => setToken('token')).toThrow('Storage quota exceeded');
      expect(console.error).toHaveBeenCalledWith('Error setting token:', error);
    });
  });

  describe('getToken', () => {
    it('should retrieve token from localStorage', () => {
      const token = 'stored-token-456';
      localStorage.setItem('access_token', token);
      
      const result = getToken();
      
      expect(localStorage.getItem).toHaveBeenCalledWith('access_token');
      expect(result).toBe(token);
    });

    it('should return null when no token exists', () => {
      const result = getToken();
      
      expect(result).toBeNull();
    });

    it('should handle localStorage errors and return null', () => {
      const error = new Error('localStorage not available');
      localStorage.getItem.mockImplementation(() => {
        throw error;
      });

      const result = getToken();
      
      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalledWith('Error getting token:', error);
    });
  });

  describe('removeToken', () => {
    it('should remove both access_token and user from localStorage', () => {
      removeToken();
      
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('user');
      expect(localStorage.removeItem).toHaveBeenCalledTimes(2);
    });

    it('should handle localStorage errors gracefully', () => {
      const error = new Error('Remove failed');
      localStorage.removeItem.mockImplementation(() => {
        throw error;
      });

      // Should not throw
      expect(() => removeToken()).not.toThrow();
      expect(console.error).toHaveBeenCalledWith('Error removing token:', error);
    });
  });

  describe('decodeToken', () => {
    it('should decode a provided token', () => {
      const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test';
      const decodedPayload = {
        sub: 'user-123',
        email: 'test@example.com',
        exp: 1234567890,
      };
      
      jwtDecode.mockReturnValue(decodedPayload);
      
      const result = decodeToken(token);
      
      expect(jwtDecode).toHaveBeenCalledWith(token);
      expect(result).toEqual(decodedPayload);
    });

    it('should decode token from localStorage when no token provided', () => {
      const storedToken = 'stored-jwt-token';
      const decodedPayload = {
        sub: 'user-456',
        email: 'stored@example.com',
        exp: 1234567890,
      };
      
      localStorage.setItem('access_token', storedToken);
      jwtDecode.mockReturnValue(decodedPayload);
      
      const result = decodeToken();
      
      expect(localStorage.getItem).toHaveBeenCalledWith('access_token');
      expect(jwtDecode).toHaveBeenCalledWith(storedToken);
      expect(result).toEqual(decodedPayload);
    });

    it('should return null when no token exists', () => {
      const result = decodeToken();
      
      expect(result).toBeNull();
      expect(jwtDecode).not.toHaveBeenCalled();
    });

    it('should return null when token is invalid', () => {
      const invalidToken = 'invalid-token';
      const error = new Error('Invalid token');
      
      jwtDecode.mockImplementation(() => {
        throw error;
      });
      
      const result = decodeToken(invalidToken);
      
      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalledWith('Error decoding token:', error);
    });
  });

  describe('isTokenExpired', () => {
    let dateNowSpy;
    
    beforeEach(() => {
      // Mock Date.now() to return a fixed timestamp
      // 1000 seconds * 1000 = 1000000 milliseconds
      dateNowSpy = jest.spyOn(Date, 'now').mockReturnValue(1000 * 1000); // 1000 seconds in milliseconds
    });

    afterEach(() => {
      if (dateNowSpy) {
        dateNowSpy.mockRestore();
      }
    });

    it('should return false for non-expired token', () => {
      const token = 'valid-token';
      const futureExp = 2000; // 2000 seconds (future)
      const decodedToken = { exp: futureExp };
      
      jwtDecode.mockImplementation(() => decodedToken);
      
      const result = isTokenExpired(token);
      
      expect(result).toBe(false);
    });

    it('should return true for expired token', () => {
      const pastExp = 500; // 500 seconds (past)
      const decodedToken = { exp: pastExp };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = isTokenExpired('expired-token');
      
      expect(result).toBe(true);
    });

    it('should return true for token expiring within 10 second buffer', () => {
      // Current time: 1000 seconds
      // Token expires at: 1005 seconds (within 10 second buffer)
      const nearExpiry = 1005;
      const decodedToken = { exp: nearExpiry };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = isTokenExpired('near-expiry-token');
      
      expect(result).toBe(true);
    });

    it('should return true when token has no exp field', () => {
      const decodedToken = { sub: 'user-123' }; // No exp field
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = isTokenExpired('no-exp-token');
      
      expect(result).toBe(true);
    });

    it('should return true when token is null', () => {
      const result = isTokenExpired();
      
      expect(result).toBe(true);
    });

    it('should return true when decoding fails', () => {
      jwtDecode.mockImplementation(() => {
        throw new Error('Decode error');
      });
      
      const result = isTokenExpired('invalid-token');
      
      expect(result).toBe(true);
    });
  });

  describe('isAuthenticated', () => {
    let dateNowSpy;
    
    beforeEach(() => {
      dateNowSpy = jest.spyOn(Date, 'now').mockReturnValue(1000 * 1000); // 1000 seconds in milliseconds
    });

    afterEach(() => {
      if (dateNowSpy) {
        dateNowSpy.mockRestore();
      }
    });

    it('should return true when valid token exists', () => {
      const validToken = 'valid-jwt-token';
      const futureExp = 2000;
      const decodedToken = { exp: futureExp };
      
      localStorage.setItem('access_token', validToken);
      jwtDecode.mockImplementation(() => decodedToken);
      
      const result = isAuthenticated();
      
      expect(result).toBe(true);
    });

    it('should return false when no token exists', () => {
      const result = isAuthenticated();
      
      expect(result).toBe(false);
    });

    it('should return false when token is expired', () => {
      const expiredToken = 'expired-jwt-token';
      const pastExp = 500;
      const decodedToken = { exp: pastExp };
      
      localStorage.setItem('access_token', expiredToken);
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = isAuthenticated();
      
      expect(result).toBe(false);
    });
  });

  describe('getUserFromToken', () => {
    it('should extract user information from token', () => {
      const token = 'jwt-token-with-user-data';
      const decodedToken = {
        sub: 'user-uuid-123',
        email: 'user@example.com',
        username: 'testuser',
        display_name: 'Test User',
        exp: 1234567890,
      };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getUserFromToken(token);
      
      expect(result).toEqual({
        userId: 'user-uuid-123',
        email: 'user@example.com',
        username: 'testuser',
        displayName: 'Test User',
        exp: 1234567890,
      });
    });

    it('should use stored token when no token provided', () => {
      const storedToken = 'stored-jwt-token';
      const decodedToken = {
        sub: 'user-456',
        email: 'stored@example.com',
        username: 'storeduser',
        display_name: 'Stored User',
        exp: 9876543210,
      };
      
      localStorage.setItem('access_token', storedToken);
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getUserFromToken();
      
      expect(result).toEqual({
        userId: 'user-456',
        email: 'stored@example.com',
        username: 'storeduser',
        displayName: 'Stored User',
        exp: 9876543210,
      });
    });

    it('should return null when token cannot be decoded', () => {
      const result = getUserFromToken();
      
      expect(result).toBeNull();
    });

    it('should handle decoding errors', () => {
      jwtDecode.mockImplementation(() => {
        throw new Error('Invalid token');
      });
      
      const result = getUserFromToken('invalid-token');
      
      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('getTokenExpiration', () => {
    it('should return expiration date from token', () => {
      const token = 'jwt-token';
      const expTimestamp = 1234567890; // Unix timestamp in seconds
      const decodedToken = { exp: expTimestamp };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getTokenExpiration(token);
      
      // Convert seconds to milliseconds for Date object
      expect(result).toEqual(new Date(expTimestamp * 1000));
    });

    it('should use stored token when no token provided', () => {
      const storedToken = 'stored-token';
      const expTimestamp = 9876543210;
      const decodedToken = { exp: expTimestamp };
      
      localStorage.setItem('access_token', storedToken);
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getTokenExpiration();
      
      expect(result).toEqual(new Date(expTimestamp * 1000));
    });

    it('should return null when token has no exp field', () => {
      const decodedToken = { sub: 'user-123' };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getTokenExpiration('token');
      
      expect(result).toBeNull();
    });

    it('should return null when token cannot be decoded', () => {
      const result = getTokenExpiration();
      
      expect(result).toBeNull();
    });

    it('should handle decoding errors', () => {
      jwtDecode.mockImplementation(() => {
        throw new Error('Decode error');
      });
      
      const result = getTokenExpiration('invalid-token');
      
      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('getTokenRemainingTime', () => {
    beforeEach(() => {
      // Mock Date.now() to return 1000 seconds (in milliseconds)
      jest.spyOn(Date, 'now').mockReturnValue(1000000);
    });

    afterEach(() => {
      Date.now.mockRestore();
    });

    it('should return remaining time in seconds', () => {
      const expTimestamp = 2000; // Expires at 2000 seconds
      const decodedToken = { exp: expTimestamp };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getTokenRemainingTime('token');
      
      // Current: 1000 seconds, Expiry: 2000 seconds
      // Remaining: 1000 seconds
      expect(result).toBe(1000);
    });

    it('should return 0 for expired token', () => {
      const expTimestamp = 500; // Already expired
      const decodedToken = { exp: expTimestamp };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getTokenRemainingTime('expired-token');
      
      expect(result).toBe(0);
    });

    it('should use stored token when no token provided', () => {
      const storedToken = 'stored-token';
      const expTimestamp = 1500;
      const decodedToken = { exp: expTimestamp };
      
      localStorage.setItem('access_token', storedToken);
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getTokenRemainingTime();
      
      expect(result).toBe(500);
    });

    it('should return 0 when token has no exp field', () => {
      const decodedToken = { sub: 'user-123' };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getTokenRemainingTime('token');
      
      expect(result).toBe(0);
    });

    it('should return 0 when token cannot be decoded', () => {
      const result = getTokenRemainingTime();
      
      expect(result).toBe(0);
    });

    it('should floor the remaining time', () => {
      const expTimestamp = 1500.7; // 1500.7 seconds
      const decodedToken = { exp: expTimestamp };
      
      jwtDecode.mockReturnValue(decodedToken);
      
      const result = getTokenRemainingTime('token');
      
      // Should floor 500.7 to 500
      expect(result).toBe(500);
    });

    it('should handle decoding errors', () => {
      jwtDecode.mockImplementation(() => {
        throw new Error('Decode error');
      });
      
      const result = getTokenRemainingTime('invalid-token');
      
      expect(result).toBe(0);
      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('Integration tests', () => {
    let dateNowSpy;
    
    beforeEach(() => {
      dateNowSpy = jest.spyOn(Date, 'now').mockReturnValue(1000 * 1000); // 1000 seconds in milliseconds
    });

    afterEach(() => {
      if (dateNowSpy) {
        dateNowSpy.mockRestore();
      }
    });

    it('should handle complete authentication flow', () => {
      const token = 'jwt-token-123';
      const decodedToken = {
        sub: 'user-uuid',
        email: 'test@example.com',
        username: 'testuser',
        display_name: 'Test User',
        exp: 2000, // Future expiration
      };
      
      jwtDecode.mockImplementation(() => decodedToken);
      
      // Set token
      setToken(token);
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', token);
      
      // Get token
      expect(getToken()).toBe(token);
      
      // Check authentication
      expect(isAuthenticated()).toBe(true);
      
      // Get user info
      const user = getUserFromToken();
      expect(user.email).toBe('test@example.com');
      
      // Remove token
      removeToken();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('user');
    });

    it('should handle expired token flow', () => {
      const token = 'expired-jwt-token';
      const decodedToken = {
        sub: 'user-uuid',
        email: 'test@example.com',
        exp: 500, // Past expiration
      };
      
      localStorage.setItem('access_token', token);
      jwtDecode.mockReturnValue(decodedToken);
      
      // Token exists but is expired
      expect(getToken()).toBe(token);
      expect(isTokenExpired()).toBe(true);
      expect(isAuthenticated()).toBe(false);
      expect(getTokenRemainingTime()).toBe(0);
    });
  });
});
