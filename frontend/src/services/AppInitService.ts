/**
 * AppInitService.ts
 * 
 * Handles application initialization tasks, including setting up authentication,
 * loading configuration, and preparing the application for use.
 */

import tokenService from './TokenService';
import backendApi from '../api/backend_api_interface';

// Development mode detection
const isDevelopmentMode = (): boolean => {
  return process.env.NODE_ENV === 'development' || window.location.hostname === 'localhost';
};

class AppInitService {
  /**
   * Initialize the application
   * This should be called as early as possible in the application lifecycle
   */
  async initialize(): Promise<void> {
    console.log('AppInitService: Initializing application...');
    
    // Initialize authentication
    await this.initializeAuthentication();
    
    console.log('AppInitService: Application initialized successfully');
  }

  /**
   * Initialize authentication
   * Ensures the authentication system is properly set up
   */
  private async initializeAuthentication(): Promise<void> {
    console.log('AppInitService: Initializing authentication...');
    
    // Check if we're in development mode
    if (isDevelopmentMode()) {
      console.log('AppInitService: Running in development mode');
      
      // If no token exists, create a development token
      if (!tokenService.getToken()) {
        console.log('AppInitService: No token found, creating development token');
        const devToken = tokenService.createDevelopmentToken();
        tokenService.setToken(devToken);
        backendApi.setAuthToken(devToken);
      } else {
        console.log('AppInitService: Using existing token');
        // Ensure the API client has the token
        const existingToken = tokenService.getToken();
        if (existingToken) {
          backendApi.setAuthToken(existingToken);
        }
      }
    } else {
      console.log('AppInitService: Running in production mode');
      
      // In production, just ensure the API client has any existing token
      const token = tokenService.getToken();
      if (token && tokenService.isTokenValid()) {
        console.log('AppInitService: Valid token found, setting in API client');
        backendApi.setAuthToken(token);
      } else if (token) {
        console.log('AppInitService: Invalid token found, clearing');
        tokenService.clearToken();
        backendApi.setAuthToken(null);
      }
    }
  }
}

// Export a singleton instance
const appInitService = new AppInitService();
export default appInitService;
