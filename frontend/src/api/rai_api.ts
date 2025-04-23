/**
 * Unified RAI API Client
 * Provides methods to interact with all RAI backend services.
 */

// Define Message type inline to avoid dependency on external module
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  messageType?: string;
  isSearchMessage?: boolean;
}

// --- Type Definitions ---

// Base API response interface
export interface ApiResponse {
  status?: 'success' | 'error' | string; // Allow other status values
  message?: string;
  error?: string;
  success?: boolean; // Add success flag for compatibility
}

// Session interface
export interface Session {
  id: string;
  title: string;
  timestamp: string;
  last_modified: string;
}

// API response interfaces
export interface HealthStatus extends ApiResponse {
  version: string;
  uptime: number;
}
// Custom response type for chat messages
export interface SendMessageResponse {
  // We're not extending ApiResponse to avoid type conflicts with the message property
  status?: 'success' | 'error' | string; // From ApiResponse
  error?: string; // From ApiResponse
  success?: boolean; // For MessageResponse compatibility 
  response?: string;
  session_id: string;
  sessionId?: string; // Alternative field name
  title?: string;
  system_message?: string;
  message_type?: string;
  system_messages?: SystemMessage[];
  llm_response?: {
    response_tiers: {
      tier1: string;
      tier2: string;
      tier3: string;
    }
  };
  // Direct tier fields that might be present
  response_tiers?: {
    tier1?: string;
    tier2?: string;
    tier3?: string;
  };
  tier1?: string;
  tier2?: string;
  tier3?: string;
  // System message related fields
  type?: string;
  action?: string;
  content?: string;
  id?: string;
  messageType?: string;
  // Search status fields - merged with the status field above
  message?: Message;
}
export interface SystemMessageResponse extends ApiResponse {
  messages: SystemMessage[];
  session_id: string;
}
export interface SystemMessage {
  id: string;
  content: string;
  type: string;
  timestamp: string | Date;
  session_id: string;
  related_message_id?: string;
}
export interface SessionsListResponse extends ApiResponse {
  sessions?: Session[];
  count?: number;
}
export interface HistoryResponse extends ApiResponse {
  messages?: Message[];
}
export interface DeleteResponse extends ApiResponse {}
export interface LLMInfoResponse extends ApiResponse {
  model_info?: any;
}
export interface LoginResponse extends ApiResponse {
  access_token?: string;
  user?: {
    user_id: number;
    username: string;
  };
}
export interface RegisterResponse extends ApiResponse {
  user?: {
    user_id: number;
    username: string;
  };
}
export interface MemoryResponse extends ApiResponse {
  user_profile_facts?: string[];
}
export interface GenerateTextResponse extends ApiResponse {
  generated_text?: string;
}
export interface ResetSessionResponse extends ApiResponse {}

// Type for fetch options
interface FetchOptions extends RequestInit {
  headers: HeadersInit & {
    'Content-Type'?: string;
    'Authorization'?: string;
  };
}

// Custom Error class for API errors
class ApiError extends Error {
  status?: number;
  data?: any;

  constructor(message: string, status?: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

import tokenService from '../services/TokenService';

// --- API Client Constants ---
const RAI_API_BASE_URL = process.env.REACT_APP_RAI_API_URL || '/api';
const LLM_API_BASE_URL = process.env.REACT_APP_LLM_API_URL || '/llm-api';

/**
 * Unified API Client for RAI Chat
 * Handles all API interactions for the application
 */
class RAIAPIClient {
  private token: string | null = null;

  constructor() {
    console.log("RAIAPIClient initialized.");
    // Initialize token from TokenService
    this.token = tokenService.getToken();
  }

  // --- Private Helper Methods ---

  /**
   * Helper function for making API requests
   */
  private async _request<T extends ApiResponse | SendMessageResponse>(
    endpoint: string, 
    method = 'GET', 
    body: object | null = null, 
    baseUrl = RAI_API_BASE_URL,
    timeoutMs = 60000 // Increased to 60 second timeout
  ): Promise<T> {
    const url = `${baseUrl}${endpoint}`;
    const options: FetchOptions = {
      method,
      headers: {
        'Content-Type': 'application/json'
      },
    };

    // Get the token from TokenService and use it if available
    const token = tokenService.getToken();
    if (token) {
      options.headers['Authorization'] = `Bearer ${token}`;
    } else if (process.env.NODE_ENV === 'development') {
      // Only in development mode, use a mock token if none is available
      const mockDevToken = process.env.REACT_APP_DEV_TOKEN || '';
      if (mockDevToken) {
        options.headers['Authorization'] = `Bearer ${mockDevToken}`;
      }
    }
    
    // Add body for non-GET requests
    if (method !== 'GET' && body) {
      options.body = JSON.stringify(body);
    }
    
    // Create an AbortController for implementing timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    options.signal = controller.signal;
    
    try {
      // Make the API request
      const response = await fetch(url, options);
      
      // Clear timeout since we got a response
      clearTimeout(timeoutId);
      
      console.log(`API Response status: ${response.status}`);
      console.log(`API Response headers:`, Array.from(response.headers).reduce((obj, [key, value]) => {
        // Use type assertion to avoid TypeScript errors with indexing
        (obj as Record<string, string>)[key] = value;
        return obj;
      }, {}));
      
      // Handle non-OK responses early to avoid parsing issues
      if (!response.ok) {
        const errorText = await response.text();
        throw new ApiError(`API request failed: ${response.statusText}`, response.status, errorText);
      }
      
      // Parse JSON response
      let data: T;
      
      // Extract session ID if available in the request body
      const getSessionId = (): string => {
        if (body && typeof body === 'object') {
          if ('session_id' in body) {
            return String(body.session_id);
          } else if ('sessionId' in body) {
            return String((body as any).sessionId);
          }
        }
        return '';
      };
      
      // Create a default fallback response
      const createDefaultResponse = (): T => {
        return {
          status: 'success',
          session_id: getSessionId(),
          response: 'No response received from server',
          message_type: 'default'
        } as unknown as T;
      };
      
      try {
        // Get content type
        const contentType = response.headers.get('Content-Type') || '';
        
        // Get the raw text response
        const text = await response.text();
        console.log(`API Response content (${text.length} chars):`, 
          text.length > 100 ? text.substring(0, 50) + '...' + text.substring(text.length - 50) : text);
        
        // If empty response, return default
        if (!text.trim()) {
          console.log('Received empty response, returning default');
          return createDefaultResponse();
        }
        
        // Try to parse the response as JSON
        try {
          // Initialize result with a default response for safety
          let result: T = createDefaultResponse();
          
          // If it's newline-delimited JSON, try to parse the best response
          if (contentType.includes('application/x-ndjson')) {
            const lines = text.split('\n').filter(line => line.trim());
            
            // If no valid lines, return default
            if (lines.length === 0) {
              result = createDefaultResponse();
            } else {
              // Try to find a valid JSON line
              let validLine = false;
              
              // Try each line until we find a valid JSON object
              for (const line of lines) {
                try {
                  result = JSON.parse(line) as T;
                  validLine = true;
                  break; // Found a valid line, stop looking
                } catch (e) {
                  console.warn(`Failed to parse JSON line: ${line}`);
                  // Continue to next line
                }
              }
              
              // If we didn't find any valid lines
              if (!validLine) {
                console.warn('Could not parse any JSON lines from ndjson response');
                result = createDefaultResponse();
              }
            }
          } else {
            // Regular JSON response
            result = JSON.parse(text) as T;
          }
          
          console.log(`API Response data:`, result);
          return result;
        } catch (jsonError) {
          console.error('JSON parse error:', jsonError);
          return createDefaultResponse();
        }
      } catch (jsonError: any) {
        console.error(`Error parsing response:`, jsonError);
        throw new ApiError(`Failed to parse response: ${jsonError.message || 'Unknown error'}`, response.status);
      }
    } catch (error) {
      // Clear the timeout to prevent memory leaks
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      
      // Handle different types of errors
      if (error instanceof ApiError) {
        console.error(`API Error: ${error.message}`);
        throw error;
      }
      
      // For AbortError (timeout or signal abort)
      if (error instanceof DOMException && error.name === 'AbortError') {
        console.error(`Request aborted: ${endpoint} - ${error.message}`);
        throw new ApiError(`Request timed out after ${timeoutMs}ms`, 408);
      }
      
      // For network errors (CORS, connection refused, etc.)
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        console.error(`Network error connecting to ${url}: ${error.message}`);
        throw new ApiError('Network connection error. Please check your internet connection.', 0);
      }
      
      // For other types of errors, create a generic API error
      const genericError = error instanceof Error ? error : new Error('An unknown network error occurred');
      console.error(`Network Error: ${genericError.message}`);
      throw new ApiError(genericError.message || 'Unknown error');
    }
  }

  /**
   * Helper function for making API requests to the LLM backend
   */
  private async _llmRequest<T extends ApiResponse | SendMessageResponse>(
    endpoint: string, 
    method = 'GET', 
    body: object | null = null
  ): Promise<T> {
    return this._request<T>(endpoint, method, body, LLM_API_BASE_URL);
  }

  // --- RAI Backend API Methods ---

  async healthCheck(): Promise<HealthStatus> {
    return this._request<HealthStatus>('/health');
  }

  /**
   * Process and normalize the API response structure
   * @private
   */
  private _processResponse(response: SendMessageResponse, sessionId: string): SendMessageResponse {
    // Ensure we have a proper response structure
    if (!response.response) {
      // If the response doesn't have a 'response' field but has content
      if (response.content) {
        response.response = response.content;
      }
      
      // If it has LLM response tiers, use those
      if (response.llm_response?.response_tiers?.tier3) {
        response.response = response.llm_response.response_tiers.tier3;
      } else if (response.llm_response?.response_tiers?.tier1) {
        response.response = response.llm_response.response_tiers.tier1;
      }
    }
    
    return response;
  }

  /**
   * Handle API errors and return a standardized error response
   * @private
   */
  private _handleError(error: any, sessionId: string): SendMessageResponse {
    console.error('RAIAPIClient: Error in API call:', error);
    
    // Create a more helpful error message based on the error type
    let errorMessage = 'Unknown error occurred';
    
    if (error instanceof ApiError) {
      if (error.status === 408 || error.message.includes('timeout')) {
        errorMessage = 'The request timed out. The server might be busy or experiencing issues.';
      } else if (error.status === 0 || error.message.includes('Network')) {
        errorMessage = 'Network connection error. Please check your internet connection.';
      } else {
        errorMessage = error.message;
      }
    } else if (error instanceof Error) {
      errorMessage = error.message;
    }
    
    return {
      status: 'error',
      error: errorMessage,
      session_id: sessionId,
      response: 'I apologize, but I encountered an error while processing your request. Please try again later.',
      type: 'final'
    };
  }

  async sendMessage({ 
    sessionId, 
    message, 
    options = {}
  }: { 
    sessionId: string; 
    message: string; 
    options?: object;
  }): Promise<SendMessageResponse> {
    console.log(`RAIAPIClient: Sending message to session ${sessionId}`);
    
    try {
      // Make a direct API request to the chat endpoint with streaming=false
      // to ensure we get a standard JSON response instead of a stream
      const response = await this._request<SendMessageResponse>('/chat', 'POST', {
        session_id: sessionId,
        message,
        streaming: false, // Request non-streaming response from backend
        ...options
      });
      
      console.log('RAIAPIClient: Received response:', response);
      return response; // Backend now returns properly formatted response
    } catch (error) {
      console.error('RAIAPIClient: Error sending message:', error);
      return this._handleError(error, sessionId);
    }
  }
  
  /**
   * Stream a message from the chat API
   * This now uses the same non-streaming approach as sendMessage but with callback
   */
  async streamMessage({ 
    sessionId, 
    message, 
    options = {},
    onUpdate = (chunk: any) => {}
  }: { 
    sessionId: string; 
    message: string; 
    options?: object;
    onUpdate?: (chunk: any) => void;
  }): Promise<SendMessageResponse> {
    try {
      // Make a direct API request with a longer timeout (120 seconds)
      // Using streaming: false to ensure we get a standard JSON response
      const response = await this._request<SendMessageResponse>('/chat', 'POST', {
        session_id: sessionId,
        message,
        streaming: false, // Request non-streaming response
        ...options
      }, RAI_API_BASE_URL, 120000);
      
      console.log('RAIAPIClient: streamMessage received response:', response);
      
      // Call the onUpdate callback with the final response
      onUpdate({
        type: 'final',
        ...response
      });
      
      return response;
    } catch (error) {
      console.error('RAIAPIClient: Error in streamMessage:', error);
      const errorResponse = this._handleError(error, sessionId);
      onUpdate(errorResponse);
      return errorResponse;
    }
  }

  async createSystemMessage(
    sessionId: string, 
    content: string, 
    type: string, 
    relatedMessageId?: string
  ): Promise<SystemMessageResponse> {
    return this._request<SystemMessageResponse>('/system-messages', 'POST', {
      session_id: sessionId,
      content,
      type,
      related_message_id: relatedMessageId
    });
  }

  /**
   * Fetch system messages from the dedicated system-messages endpoint
   * This allows separate handling of system operational messages vs. actual LLM responses
   * @param action The action to fetch status for (e.g., 'get_search_status')
   * @param session_id The session ID to fetch status for
   * @returns Promise containing system message data
   */
  async getSystemMessage(action: string, session_id: string): Promise<SystemMessageResponse> {
    console.log(`RAIAPIClient: Fetching system message for session ${session_id}, action: ${action}`);
    
    try {
      // Use the dedicated system-messages endpoint
      const response = await this._request<SystemMessageResponse>('/system-messages', 'POST', {
        action,
        session_id
      });
      
      console.log('RAIAPIClient: Received system message:', response);
      return response;
    } catch (error) {
      console.error('RAIAPIClient: Error fetching system message:', error);
      // Return a default error system message that matches SystemMessageResponse
      return {
        messages: [{
          id: `sys-error-${Date.now()}`,
          content: `Error fetching ${action} status`,
          type: 'error',
          timestamp: new Date().toISOString(),
          session_id: session_id
        }],
        session_id: session_id
      };
    }
  }

  async getChatSessions(): Promise<SessionsListResponse> {
    return this._request<SessionsListResponse>('/sessions', 'GET');
  }

  async getChatHistory(sessionId: string): Promise<HistoryResponse> {
    if (!sessionId) {
      throw new Error("sessionId is required to fetch chat history.");
    }
    
    const response = await this._request<HistoryResponse>(`/sessions/${sessionId}/history`);
    
    // Convert timestamps to Date objects
    if (response.messages && Array.isArray(response.messages)) {
      response.messages = response.messages.map((msg): Message => {
        let timestamp: Date;
        
        try {
          if (typeof msg.timestamp === 'string') {
            timestamp = new Date(msg.timestamp);
          } else if (msg.timestamp instanceof Date) {
            timestamp = msg.timestamp;
          } else {
            timestamp = new Date();
          }
          
          return { ...msg, timestamp };
        } catch (error) {
          return { ...msg, timestamp: new Date() };
        }
      });
    }
    
    return response;
  }

  async deleteChatSession(sessionId: string): Promise<DeleteResponse> {
    return this._request<DeleteResponse>(`/sessions/${sessionId}`, 'DELETE');
  }

  async getLLMInfo(): Promise<LLMInfoResponse> {
    return this._request<LLMInfoResponse>('/llm/info');
  }

  async getMemory(): Promise<MemoryResponse> {
    return this._request<MemoryResponse>('/memory');
  }

  async generateText(prompt: string, options: object = {}): Promise<GenerateTextResponse> {
    return this._request<GenerateTextResponse>('/generate', 'POST', { prompt, ...options });
  }

  async resetSession(): Promise<ResetSessionResponse> {
    return this._request<ResetSessionResponse>('/session/reset', 'POST');
  }

  setAuthToken(token: string | null): void {
    // Update the instance token property
    this.token = token;
    
    // Use TokenService to store the token
    tokenService.setToken(token);
  }

  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await this._request<LoginResponse>('/api/auth/login', 'POST', { username, password });
    
    if (response.access_token) {
      this.setAuthToken(response.access_token);
    }
    
    return response;
  }

  async register(username: string, password: string): Promise<RegisterResponse> {
    return this._request<RegisterResponse>('/api/auth/register', 'POST', { username, password });
  }

  // --- LLM API Methods ---

  async llmHealthCheck(): Promise<HealthStatus> {
    return this._llmRequest<HealthStatus>('/health');
  }

  async getLLMModels(): Promise<string[]> {
    const response = await this._llmRequest<ApiResponse & { models?: string[] }>('/models');
    return response.models || [];
  }

  async chatCompletion(
    messages: Array<{role: string, content: string}>, 
    options: object = {}
  ): Promise<SendMessageResponse> {
    return this._llmRequest<SendMessageResponse>('/chat', 'POST', { messages, ...options });
  }
  
  /**
   * Check the status of a web search for a session
   * @param sessionId The session ID to check status for
   * @returns Promise resolving to a response with search status
   */
  async checkSearchStatus(sessionId: string): Promise<SendMessageResponse> {
    console.log(`RAIAPIClient: Checking search status for session ${sessionId}`);
    return this._request<SendMessageResponse>(`/search-status/${sessionId}`, 'GET');
  }
}

// Export singleton instance
const raiAPIClient = new RAIAPIClient();
export default raiAPIClient;
