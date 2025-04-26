/**
 * Backend API Interface for RAI Chat Frontend
 *
 * This module serves as the single entry point for all backend API interactions.
 * All components should use this interface rather than directly calling the backend API.
 */

import tokenService from '../services/TokenService';

// Base API response interface
export interface ApiResponse {
  status?: 'success' | 'error' | string;
  message?: string; // This is a string message about the response status
  error?: string;
  success?: boolean;
  token?: string; // JWT token for authentication responses
  user?: {  // User information for authentication responses
    user_id: number;
    username: string;
    email: string;
  };
}

// Message type definition
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  messageType?: string;
  isSearchMessage?: boolean; // Added for search messages
}

// Chat message response interface - separates from ApiResponse to avoid conflicts
export interface ChatMessageResponse {
  status?: 'success' | 'error' | 'searching' | 'search_error' | string;
  error?: string;
  success?: boolean;
  message?: Message;
  session_id: string;
  sessionId?: string; 
  response?: string;
  content?: string;
  type?: string;
  message_type?: string;
  timestamp?: string;
  action?: string;
  messageType?: string;
  id?: string;
  title?: string; // Added for session title
  
  // Search-specific fields
  raw_results?: any[] | any; // Search results array or object
  source?: string;
  query?: string;
  search_type?: string;

  system_messages?: Array<{
    content: string;
    type: string;
    id: string;
  }>;
  messages?: Array<Message>; // For chat history responses
  llm_response?: {
    response_tiers?: {
      tier1?: string;
      tier2?: string;
      tier3?: string;
    }
  };
  response_tiers?: {
    tier1?: string;
    tier2?: string;
    tier3?: string;
  };
  tier1?: string;
  tier2?: string;
  tier3?: string;
}

// Session interface
export interface Session {
  id: string;
  title: string;
  timestamp: string;
  last_modified: string;
}

// Fetch options type
interface FetchOptions {
  method: string;
  headers: Record<string, string>;
  body?: string;
  signal?: AbortSignal;
}

// Custom error class for API errors
export class ApiError extends Error {
  status: number;
  responseText: string;

  constructor(message: string, status: number = 500, responseText: string = '') {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.responseText = responseText;
  }
}

class BackendApiClient {
  private baseUrl: string;
  
  constructor() {
    // Get base URL from environment variables with fallback
    this.baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:6102/api';
    console.log(`Initializing Backend API client with URL: ${this.baseUrl}`);
  }

  /**
   * Helper function for making API requests
   */
  private async request<T>(
    endpoint: string, 
    method = 'GET', 
    body: object | null = null,
    timeoutMs = 60000
  ): Promise<T> {
    // Construct the full URL (avoid double slashes)
    const url = endpoint ? 
      // Make sure we don't add an extra slash if baseUrl ends with one
      `${this.baseUrl.endsWith('/') ? this.baseUrl.slice(0, -1) : this.baseUrl}/${endpoint}` : 
      this.baseUrl;
    
    console.log('Making API request to:', url, 'with method:', method);
    
    // Set up request options
    const options: FetchOptions = {
      method,
      headers: {
        'Content-Type': 'application/json'
      },
    };

    // Add authentication token if available
    const token = tokenService.getToken();
    if (token) {
      options.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Add request body for non-GET requests
    if (body && method !== 'GET') {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    
    // Set up timeout handling
    const controller = new AbortController();
    options.signal = controller.signal;
    
    // Create timeout that will abort the request if it takes too long
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, timeoutMs);
    
    try {
      // Make the API request
      const response = await fetch(url, options);
      
      // Log raw network response for debugging
      console.log(`API Response Status:`, response.status, response.statusText);
      
      // Log headers in a way that works with the TypeScript target
      const headerInfo: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        headerInfo[key] = value;
      });
      console.log(`API Response Headers:`, JSON.stringify(headerInfo));
      
      const responseText = await response.text();
      console.log(`API Response Raw Text (first 500 chars):`, responseText.substring(0, 500) + (responseText.length > 500 ? '...' : ''));
      
      // Clear timeout since request completed
      clearTimeout(timeoutId);
      
      // Get response text
      // Parse the response as JSON
      let responseData: any;
      try {
        responseData = JSON.parse(responseText);
        console.log(`STAGE 1 - API Response Parsed:`, JSON.stringify(responseData));
        console.log(`STAGE 1 - Response keys:`, Object.keys(responseData));
        if (responseData.content) console.log(`STAGE 1 - Content field:`, responseData.content);
        if (responseData.message?.content) console.log(`STAGE 1 - Message.content field:`, responseData.message.content);
      } catch (e) {
        console.error('Error parsing response as JSON:', e);
        throw new ApiError(`Invalid JSON response: ${responseText.substring(0, 100)}...`, 500, responseText);
      }
      
      // Check if response is successful
      if (!response.ok) {
        throw new ApiError(responseData.message || `API Error: ${response.status} ${response.statusText}`, response.status, responseText);
      }
      
      // Handle empty responses
      if (!responseData) {
        return {} as T;
      }
      
      return responseData as T;
    } catch (error: any) {
      // Clear timeout if there was an error
      clearTimeout(timeoutId);
      
      if (error instanceof ApiError) {
        throw error;
      }
      
      // Handle abort errors
      if (error.name === 'AbortError') {
        throw new ApiError('Request timed out', 408);
      }
      
      throw new ApiError(`Network error: ${error.message}`, 0);
    }
  }

  /**
   * Send a message to the chat API
   */
  async sendMessage(
    sessionId: string, 
    message: string, 
    options: object = {}
  ): Promise<ChatMessageResponse> {
    try {
      console.log('BackendApiClient: Sending message to session:', sessionId);
      // Make the API request
      const response = await this.request<any>(`chat`, 'POST', {
        session_id: sessionId,
        message,
        ...options
      });
      
      // Add detailed debug logging to examine response structure
      console.log('BackendApiClient: Raw API response:', JSON.stringify(response));
      console.log('BackendApiClient: Raw response keys:', Object.keys(response));
      
      // Log any content/message fields for debugging
      if (response.content) console.log('BackendApiClient: Content field:', response.content);
      if (response.message?.content) console.log('BackendApiClient: Message.content field:', response.message.content);
      
      // Return the response with minimal changes
      // Just ensure session IDs are consistent and properly typed
      return {
        ...response,
        // Ensure sessionId is always present for frontend
        sessionId: response.sessionId || response.session_id || sessionId
      };
    } catch (error) {
      console.error('BackendApiClient: Error sending message:', error);
      
      // Create a fallback response
      return {
        status: 'error',
        session_id: sessionId,
        response: error instanceof ApiError 
          ? `Error: ${error.message}` 
          : 'An unexpected error occurred',
        type: 'final'
      };
    }
  }

  /**
   * Stream a message from the chat API
   */
  async streamMessage(
    sessionId: string, 
    message: string, 
    onChunk: (chunk: ChatMessageResponse) => void,
    options: object = {}
  ): Promise<ChatMessageResponse> {
    try {
      // Make request with longer timeout
      const response = await this.request<ChatMessageResponse>('chat', 'POST', {
        session_id: sessionId,
        message,
        streaming: true,
        ...options
      }, 120000);
      
      console.log('BackendApiClient: Stream message response:', response);
      
      // Call the onChunk callback with final response
      onChunk({
        type: 'final',
        ...response
      });
      
      return response;
    } catch (error) {
      console.error('BackendApiClient: Error in stream message:', error);
      
      // Create error response
      const errorResponse = {
        status: 'error',
        session_id: sessionId,
        response: error instanceof ApiError 
          ? `Error: ${error.message}` 
          : 'An unexpected error occurred',
        type: 'final'
      };
      
      onChunk(errorResponse);
      return errorResponse;
    }
  }

  /**
   * Get all sessions for the current user
   */
  async getSessions(): Promise<Session[]> {
    try {
      const response = await this.request<{sessions: Session[]}>('sessions', 'GET');
      return response.sessions || [];
    } catch (error) {
      console.error('BackendApiClient: Error fetching sessions:', error);
      return [];
    }
  }

  /**
   * Get a specific session by ID
   */
  async getSession(sessionId: string): Promise<Session | null> {
    try {
      return await this.request<Session>(`sessions/${sessionId}`, 'GET');
    } catch (error) {
      console.error(`BackendApiClient: Error fetching session ${sessionId}:`, error);
      return null;
    }
  }

  /**
   * Create a new session
   */
  async createSession(title: string = 'New Chat'): Promise<Session | null> {
    try {
      return await this.request<Session>('sessions', 'POST', { title });
    } catch (error) {
      console.error('BackendApiClient: Error creating session:', error);
      return null;
    }
  }

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<boolean> {
    try {
      await this.request<ApiResponse>(`sessions/${sessionId}`, 'DELETE');
      return true;
    } catch (error) {
      console.error(`BackendApiClient: Error deleting session ${sessionId}:`, error);
      return false;
    }
  }

  /**
   * Get chat history for a session
   */
  async getChatHistory(sessionId: string): Promise<{messages: Array<any>, success: boolean}> {
    try {
      return await this.request<{messages: Array<any>, success: boolean}>(`sessions/${sessionId}/messages`, 'GET');
    } catch (error) {
      console.error(`BackendApiClient: Error fetching chat history for session ${sessionId}:`, error);
      return { messages: [], success: false };
    }
  }

  /**
   * Get system message status
   */
  async getSystemMessage(action: string, sessionId: string): Promise<ChatMessageResponse> {
    try {
      return await this.request<ChatMessageResponse>(`system-messages/${action}`, 'GET', {
        session_id: sessionId
      });
    } catch (error) {
      console.error(`BackendApiClient: Error fetching system message for action ${action}:`, error);
      return {
        status: 'error',
        session_id: sessionId,
        response: error instanceof ApiError 
          ? `Error: ${error.message}` 
          : 'An unexpected error occurred'
      };
    }
  }

  /**
   * Create a system message
   */
  async createSystemMessage(
    sessionId: string,
    content: string,
    type: string,
    relatedMessageId?: string
  ): Promise<ApiResponse> {
    try {
      return await this.request<ApiResponse>(`sessions/${sessionId}/system-messages`, 'POST', {
        content,
        type,
        related_message_id: relatedMessageId
      });
    } catch (error) {
      console.error('BackendApiClient: Error creating system message:', error);
      return { status: 'error', message: 'Failed to create system message' };
    }
  }

  /**
   * Get system messages for a session
   */
  async getSystemMessages(sessionId: string): Promise<{ messages: Message[] }> {
    try {
      return await this.request<{ messages: Message[] }>(`sessions/${sessionId}/system-messages`, 'GET');
    } catch (error) {
      console.error('BackendApiClient: Error getting system messages:', error);
      return { messages: [] };
    }
  }

  /**
   * Check backend health status
   */
  async healthCheck(): Promise<ApiResponse> {
    try {
      return await this.request<ApiResponse>('health', 'GET');
    } catch (error) {
      console.error('BackendApiClient: Health check failed:', error);
      return { status: 'error', message: 'Health check failed' };
    }
  }

  /**
   * Get all available chat sessions
   */
  async getChatSessions(): Promise<{sessions: Session[], success: boolean}> {
    try {
      return await this.request<{sessions: Session[], success: boolean}>('sessions', 'GET');
    } catch (error) {
      console.error('BackendApiClient: Error fetching sessions:', error);
      return { sessions: [], success: false };
    }
  }

  /**
   * Delete a chat session
   */
  async deleteChatSession(sessionId: string): Promise<ApiResponse> {
    try {
      return await this.request<ApiResponse>(`sessions/${sessionId}`, 'DELETE');
    } catch (error) {
      console.error(`BackendApiClient: Error deleting session ${sessionId}:`, error);
      return { status: 'error', message: 'Failed to delete session' };
    }
  }

  /**
   * Logout the current user
   */
  async logout(): Promise<ApiResponse> {
    try {
      return await this.request<ApiResponse>('auth/logout', 'POST');
    } catch (error) {
      console.error('BackendApiClient: Error logging out user:', error);
      return { status: 'error', message: 'Failed to logout user' };
    }
  }

  /**
   * Reset the current session
   */
  async resetSession(): Promise<any> {
    try {
      return await this.request<any>('sessions/reset', 'POST');
    } catch (error) {
      console.error('BackendApiClient: Error resetting session:', error);
      return { status: 'error', message: 'Failed to reset session' };
    }
  }

  /**
   * Set the authentication token for API requests
   */
  setAuthToken(token: string | null): void {
    if (token) {
      console.log('BackendApiClient: Setting auth token');
      tokenService.setToken(token);
    } else {
      console.log('BackendApiClient: Clearing auth token');
      tokenService.clearToken();
    }
  }

  /**
   * Register a new user
   */
  async register(username: string, email: string, password: string): Promise<ApiResponse> {
    try {
      return await this.request<ApiResponse>('auth/register', 'POST', {
        username,
        email,
        password
      });
    } catch (error) {
      console.error('BackendApiClient: Error registering user:', error);
      return { status: 'error', message: 'Failed to register user' };
    }
  }

  /**
   * Login a user
   */
  async login(email: string, password: string): Promise<ApiResponse> {
    try {
      return await this.request<ApiResponse>('auth/login', 'POST', {
        email,
        password
      });
    } catch (error) {
      console.error('BackendApiClient: Error logging in user:', error);
      return { status: 'error', message: 'Failed to login user' };
    }
  }
}

// Singleton instance
let _backendApiClient: BackendApiClient | null = null;

/**
 * Get the singleton instance of the Backend API client
 */
export function getBackendApi(): BackendApiClient {
  if (_backendApiClient === null) {
    _backendApiClient = new BackendApiClient();
  }
  return _backendApiClient;
}

// Export default instance for convenience
export default getBackendApi();
