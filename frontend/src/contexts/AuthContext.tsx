import React, { createContext, useState, useContext, useEffect, ReactNode, useCallback } from 'react';
import backendApi, { Session, ApiResponse } from '../api/backend_api_interface';
import tokenService from '../services/TokenService';

// Import Session type

interface AuthState {
  token: string | null;
  user: { username: string; email?: string; user_id?: number } | null; // Made email optional
  sessions: Session[] | null; // Added state for sessions
  isLoading: boolean;
  error: string | null;
  isFetchingSessions: boolean; // Added loading state for sessions
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>; // Updated to use email
  register: (username: string, email: string, password: string) => Promise<void>; // Updated to include email
  logout: () => void;
  isAuthenticated: () => boolean;
  fetchUserSessions: () => Promise<void>; // Expose fetch function
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const log = console.log; // Use console.log for web logging
  log("--- AuthProvider Render ---");

  const [authState, setAuthState] = useState<AuthState>({
    token: tokenService.getToken(), // Initialize from localStorage
    user: null,
    sessions: null,
    isLoading: false,
    error: null,
    isFetchingSessions: false,
  });

  // Function to fetch sessions (memoized with useCallback)
  const fetchUserSessions = useCallback(async () => {
    log("AuthContext: Attempting to fetch user sessions...");
    setAuthState(prev => ({ ...prev, isFetchingSessions: true, error: null }));

    // Get token directly from state as it should be synced with localStorage
    const currentToken = authState.token;

    if (!currentToken) {
      log("AuthContext: Cannot fetch sessions, no token available.");
      setAuthState(prev => ({ 
        ...prev, 
        isFetchingSessions: false,
        error: "Authentication required"
      }));
      return;
    }

    try {
      // Ensure API client has the latest token
      backendApi.setAuthToken(currentToken);
      log(`AuthContext: fetchUserSessions - Calling API with token`);

      // Call the real backend API
      const response = await backendApi.getChatSessions(); 

      if (response && response.success) {
        const fetchedSessions = (Array.isArray(response.sessions)) ? response.sessions : null;
        if (fetchedSessions === null && response.sessions) {
          log(`AuthContext: API returned 'sessions' but it was not an array. Type: ${typeof response.sessions}`);
        }
        log(`AuthContext: Successfully processed fetch. Sessions count: ${fetchedSessions?.length ?? 0}.`);
        setAuthState(prev => ({ ...prev, sessions: fetchedSessions, isFetchingSessions: false }));
      } else {
        throw new Error(response.success === false ? 'Failed to fetch sessions' : 'Invalid response');
      }
    } catch (err: any) {
      log(`AuthContext: Error fetching sessions: ${err?.message}`);
      
      setAuthState(prev => ({ 
        ...prev, 
        isFetchingSessions: false,
        error: "Failed to load sessions"
      }));
    }
  }, [authState.token]); // Depend on token

  // Auto-authenticate on mount if token exists
  useEffect(() => {
    const savedToken = tokenService.getToken();
    
    if (savedToken) {
      log("AuthProvider Mount: Token found, retrieving session...");
      
      // Set the token in the API client
      backendApi.setAuthToken(savedToken);
      
      // Get user info from token (or if needed, fetch from /api/me endpoint)
      const userInfo = tokenService.getUserFromToken();
      
      if (userInfo) {
        setAuthState(prev => ({ 
          ...prev, 
          token: savedToken,
          user: userInfo
        }));
        
        // Fetch sessions after setting user
        fetchUserSessions();
      } else {
        // Token exists but can't get user info - might be invalid
        log("AuthProvider: Token exists but invalid. Clearing...");
        tokenService.clearToken();
        setAuthState(prev => ({ 
          ...prev, 
          token: null,
          user: null
        }));
      }
    } else {
      log("AuthProvider Mount: No saved token found");
    }
  }, []); // Run once on mount

  // Effect to fetch sessions when token changes (and is not null)
  useEffect(() => {
    if (authState.token && !authState.isLoading) {
      log("AuthProvider: Token changed/present, triggering fetchUserSessions via useEffect.");
      fetchUserSessions();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authState.token]); // Only depend on token here

  // Add a periodic refresh for sessions - gentle polling to keep chat list updated
  useEffect(() => {
    if (!authState.token) return; // Don't poll if not logged in

    // Set up a polling interval to refresh chat sessions every 20 seconds
    const interval = setInterval(() => {
      log("AuthContext: Auto-refreshing chat sessions (periodic poll)");
      fetchUserSessions();
    }, 20000); // 20 seconds

    // Clean up interval on unmount
    return () => clearInterval(interval);
  }, [authState.token, fetchUserSessions]);

  const login = async (email: string, password: string): Promise<void> => {
    log(`AuthContext: Attempting to login with email: ${email}`);
    setAuthState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      // Call the real API endpoint
      const response = await backendApi.login(email, password);
      
      if (response && response.status === 'success' && response.token) {
        // Store the token
        tokenService.setToken(response.token);
        backendApi.setAuthToken(response.token);
        
        // Update auth state with token and user info
        setAuthState(prev => ({ 
          ...prev, 
          token: response.token || null,
          user: response.user || null,
          isLoading: false,
          error: null
        }));
        
        // Sessions will be fetched via the useEffect that watches the token
        log("AuthContext: Login successful");
      } else {
        throw new Error(response?.message || 'Login failed: Invalid response');
      }
    } catch (err: any) {
      log(`AuthContext: Login error: ${err.message}`);
      const errorMessage = err.response?.data?.message || err.message || 'Login failed';
      setAuthState(prev => ({ ...prev, isLoading: false, error: errorMessage }));
      throw new Error(errorMessage);
    }
  };

  const register = async (username: string, email: string, password: string) => {
    setAuthState(prev => ({ ...prev, isLoading: true, error: null }));
    log(`AuthContext: Starting registration for ${username} (${email})`);
    
    try {
      // Call the real API endpoint
      const response = await backendApi.register(username, email, password);
      
      if (response && response.status === 'success') {
         log(`AuthContext: Registration successful for ${username}`);
         
         // Check if the API returns a token for automatic login
         if (response.token) {
           // Store the token and user info
           tokenService.setToken(response.token);
           backendApi.setAuthToken(response.token);
           
           setAuthState(prev => ({ 
             ...prev, 
             token: response.token || null,
             user: response.user || null,
             isLoading: false,
             error: null
           }));
           
           log("AuthContext: Auto-logged in after registration");
         } else {
           // Just update loading/error state if no auto-login
           setAuthState(prev => ({ ...prev, isLoading: false, error: null }));
         }
      } else {
        throw new Error(response?.message || 'Registration failed');
      }
    } catch (err: any) {
      log(`AuthContext: Register error: ${err.message}`);
      const errorMessage = err.response?.data?.message || err.message || 'Registration failed';
      setAuthState(prev => ({ ...prev, isLoading: false, error: errorMessage }));
      throw new Error(errorMessage);
    }
  };

  const logout = () => {
    log('AuthContext: Logging out user.');
    
    try {
      // Call the real logout endpoint
      backendApi.logout().then(() => {
        log('AuthContext: Logout API call successful');
      }).catch(err => {
        log(`AuthContext: Logout API call failed, but proceeding with client-side logout: ${err.message}`);
      }).finally(() => {
        // Always clear local state regardless of API response
        tokenService.clearToken();
        backendApi.setAuthToken(null); // Clear token in API client
        setAuthState({ 
          token: null, 
          user: null, 
          sessions: null, 
          isLoading: false, 
          error: null, 
          isFetchingSessions: false 
        });
        log('User logged out and token cleared.');
      });
    } catch (err: any) {
      // Even if the API call fails, proceed with client-side logout
      log(`AuthContext: Logout error, proceeding with client-side logout: ${err}`);
      tokenService.clearToken();
      backendApi.setAuthToken(null);
      setAuthState({ 
        token: null, 
        user: null, 
        sessions: null, 
        isLoading: false, 
        error: null, 
        isFetchingSessions: false 
      });
    }
  };

  const isAuthenticated = (): boolean => {
    // Could add token validation/expiry check later
    return !!authState.token;
  };

  const value = {
    ...authState,
    login,
    register,
    logout,
    isAuthenticated,
    fetchUserSessions, // Expose fetch function
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};