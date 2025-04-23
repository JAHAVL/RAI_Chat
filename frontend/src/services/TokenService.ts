/**
 * TokenService.ts
 * 
 * A centralized service for managing authentication tokens in the application.
 * Handles token storage, retrieval, validation, and provides a consistent interface
 * for all token-related operations.
 */

import { jwtDecode } from 'jwt-decode';

// Token storage key in localStorage
const TOKEN_STORAGE_KEY = 'authToken';

// Development mode detection
const isDevelopmentMode = (): boolean => {
  return process.env.NODE_ENV === 'development' || window.location.hostname === 'localhost';
};

// Interface for decoded JWT token
interface DecodedToken {
  user_id: number;
  username: string;
  exp: number;
  [key: string]: any; // Allow for additional fields
}

class TokenService {
  /**
   * Store the authentication token
   * @param token The JWT token to store
   */
  setToken(token: string | null): void {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
      console.log('TokenService: Token stored in localStorage');
    } else {
      this.clearToken();
    }
  }

  /**
   * Get the stored authentication token
   * @returns The stored token or null if not found
   */
  getToken(): string | null {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  }

  /**
   * Clear the stored authentication token
   */
  clearToken(): void {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    console.log('TokenService: Token cleared from localStorage');
  }

  /**
   * Check if a token exists and is valid
   * @returns True if a valid token exists, false otherwise
   */
  isTokenValid(): boolean {
    const token = this.getToken();
    
    if (!token) {
      return false;
    }

    try {
      // In development mode with auto-login, always consider the token valid
      if (isDevelopmentMode() && token.startsWith('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9')) {
        return true;
      }

      // Decode the token to check expiration
      const decoded = jwtDecode<DecodedToken>(token);
      const currentTime = Date.now() / 1000;
      
      // Check if token is expired
      if (decoded.exp < currentTime) {
        console.log('TokenService: Token has expired');
        return false;
      }
      
      return true;
    } catch (error) {
      console.error('TokenService: Error validating token', error);
      return false;
    }
  }

  /**
   * Get user information from the token
   * @returns User information or null if token is invalid
   */
  getUserFromToken(): { user_id: number; username: string } | null {
    const token = this.getToken();
    
    if (!token) {
      return null;
    }

    try {
      // In development mode with auto-login, return mock user
      if (isDevelopmentMode() && token.startsWith('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9')) {
        return {
          user_id: 1,
          username: 'dev_user'
        };
      }

      // Decode the token to get user info
      const decoded = jwtDecode<DecodedToken>(token);
      return {
        user_id: decoded.user_id,
        username: decoded.username
      };
    } catch (error) {
      console.error('TokenService: Error getting user from token', error);
      return null;
    }
  }

  /**
   * Create a development token for testing
   * @returns A mock JWT token
   */
  createDevelopmentToken(): string {
    // Create a properly formatted mock JWT token
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payload = btoa(JSON.stringify({ 
      user_id: 1, 
      username: 'dev_user',
      exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // 24 hours from now
    }));
    const signature = btoa('mock_signature');
    const mockToken = `${header}.${payload}.${signature}`;
    
    console.log('TokenService: Created development token');
    return mockToken;
  }
}

// Export a singleton instance
const tokenService = new TokenService();
export default tokenService;
