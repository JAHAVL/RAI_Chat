/**
 * Message Service
 * Handles all message-related operations including sending, receiving, and formatting messages.
 * This service separates business logic from UI components.
 */

import backendApi from '../../api/backend_api_interface';
import type { Message } from '../../pages/Main_Chat_UI/chat';

// Constants
export const NEW_CHAT_SESSION_ID = 'new_chat';

// Types
export interface MessageResponse {
  message: Message;
  sessionId: string;
  session_id?: string; // Sometimes backend uses this format instead
  success: boolean;
  error?: string;
  thinking?: boolean;
  status?: string;
  response?: string;
  systemMessageId?: string;
  systemMessageAction?: string;
  systemMessageStatus?: string;
  title?: string; // For new session title
  system_messages?: {
    content: string;
    type: string;
    id: string;
  }[];
  continueWaitingForResponse?: boolean; // Flag to indicate client should wait for follow-up response
  // LLM response field for tier1/tier2/tier3 content
  llm_response?: {
    response_tiers: {
      tier1?: string;
      tier2?: string;
      tier3?: string;
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
  // For system messages
  type?: string;
  action?: string;
  content?: string;
  id?: string;
  messageType?: string;
  timestamp?: string;
}

export interface MessageHistoryResponse {
  messages: Message[];
  success: boolean;
  error?: string;
}

/**
 * Message Service class to handle all message-related operations
 */
class MessageService {
  /**
   * Send a message to the backend and process the response
   * @param message The message content to send
   * @param sessionId The current session ID (null for new chat)
   * @param options Additional options for the request
   * @returns A promise containing the response message and session ID
   */
  async sendMessage(
    message: string, 
    sessionId: string | null, 
    options?: { waitForResponse?: boolean }
  ): Promise<MessageResponse> {
    console.log(`MessageService: Sending message for session ${sessionId}`);
    
    try {
      // Generate a new session ID if creating a new chat
      const session_id = sessionId === NEW_CHAT_SESSION_ID ? 
        `session-${Date.now()}-${Math.random().toString(36).substring(2, 7)}` : 
        (sessionId || `session-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`);
      
      // Send the message to the backend
      const response = await backendApi.sendMessage(
        session_id,
        message
      );
      
      console.log("MessageService: Raw backend response:", JSON.stringify(response));
      
      // No need to use 'any' - we've updated our interface to handle all response types
      
      // Check for system messages with action type
      if (response && response.type === 'system' && response.action) {
        console.log(`MessageService: Received system message with action: ${response.action}, status: ${response.status}`);
        
        // Handle different system message types (web_search, file_access, code_writing, etc.)
        if (response.action === 'web_search') {
          // Create system message with appropriate styling based on status
          const messageType = response.messageType || 
            (response.status === 'active' ? 'info' : 
             response.status === 'complete' ? 'success' : 
             response.status === 'error' ? 'error' : 'default');
          
          // Ensure content exists
          const content = response.content || 'Web search in progress...';
          
          const systemMessage = this.createSystemMessage(
            content,
            messageType
          );
          
          // Set a special ID to allow for message updating
          systemMessage.id = response.id || `sys-${Date.now()}`;
          
          // Return system message to be displayed
          return {
            message: systemMessage,
            sessionId: session_id,
            success: true,
            systemMessageId: response.id, // Store the ID for potential updates
            systemMessageAction: response.action,
            systemMessageStatus: response.status
          };
        }
      }
      
      // Only skip processing for search status messages
      // but not for actual responses containing LLM data
      if ((response.status === 'searching' || response.status === 'search_error') && 
          !response.message?.content && !response.llm_response) {
        console.log(`MessageService: Response is search status only (${response.status}), not processing as regular message.`);
        // Create a valid MessageResponse by ensuring message property exists
        return {
          message: response.message || this.createSystemMessage(`Search status: ${response.status || 'unknown'}`),
          sessionId: response.session_id || response.sessionId || session_id,
          success: response.success || true,
          status: response.status,
          systemMessageId: response.id,
          systemMessageAction: response.action,
          systemMessageStatus: response.status
        };
      }
      
      // For search complete status, we want to show a system message but also
      // continue to receive and process the actual LLM response
      if (response && response.status === 'search_complete' && !response.llm_response) {
        console.log("MessageService: Received search complete status, will return a system message");
        
        // Instead of returning early, we'll set a flag in the response to indicate
        // the client should continue waiting for the final LLM response after this status
        return {
          message: this.createSystemMessage(`Search complete. Analyzing results...`, 'success'),
          sessionId: session_id,
          success: true,
          status: 'search_complete',
          // This flag tells the client to KEEP WAITING for the final LLM response
          continueWaitingForResponse: true
        };
      }
      
      // Extract data from the response
      console.log("MessageService: Processing LLM response:", JSON.stringify(response).substring(0, 300));
      
      // The tier system contains LLM-produced responses of different verbosity:
      // - tier1: Concise version using shortest possible syntax
      // - tier2: Summary version with moderate detail
      // - tier3: Complete, detailed response
      // Use tier3 (detailed response) as the primary content to show to users
      // Define the response tiers with proper typing
      const responseTiers = response.llm_response?.response_tiers || {} as {
        tier1?: string;
        tier2?: string;
        tier3?: string;
      };
      const tier3 = responseTiers.tier3 || '';
      const tier2 = responseTiers.tier2 || '';
      const tier1 = responseTiers.tier1 || '';
      
      // Always prefer tier3 (most detailed response) when available
      // Fall back to tier2, then tier1
      let content = tier3 || response.response || tier2 || tier1 || 'No response received';
      
      // If this is a response after a web search, check for search results
      // This uses the search_complete status as an indicator
      if (response.status === 'search_complete' && response.action === 'web_search') {
        console.log('MessageService: Detected completed web search, enhancing response');
        
        // Only prepend search context if the content doesn't already mention search results
        if (!content.toLowerCase().includes('search') && 
            !content.toLowerCase().includes('found') &&
            !content.toLowerCase().includes('internet')) {
          content = `Based on my web search, I found: \n\n${content}`;
        }
      }
      
      // Create the assistant message
      const assistantMessage: Message = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content,
        timestamp: new Date(),
        isLoading: false
      };
      
      // If we got a well-formed message from the API, use its properties
      if (response.message && typeof response.message === 'object') {
        assistantMessage.id = response.message.id || assistantMessage.id;
        // Convert string timestamp to Date if needed
        assistantMessage.timestamp = typeof response.message.timestamp === 'string' ? 
          new Date(response.message.timestamp) : 
          (response.message.timestamp instanceof Date ? 
            response.message.timestamp : new Date());
      }
      
      return {
        message: assistantMessage,
        sessionId: response.session_id || sessionId || '',
        success: true,
        system_messages: response.system_messages
      };
    } catch (error) {
      console.error("MessageService: Error sending message:", error);
      
      // Get a more detailed error message
      let errorMsg = 'Error connecting to the backend server.';
      
      if (error instanceof Error) {
        // Check if it's an API error with status code
        if ('status' in error && typeof error.status === 'number') {
          if (error.status === 401 || error.status === 403) {
            errorMsg = 'Authentication error. Please log in again.';
          } else if (error.status === 404) {
            errorMsg = 'API endpoint not found. The server may be misconfigured.';
          } else if (error.status >= 500) {
            errorMsg = 'The server encountered an error. Please try again later.';
          } else {
            // Use the error message from the API if available
            errorMsg = error.message || errorMsg;
          }
        } else {
          // Network or other error
          if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
            errorMsg = 'Network error. Please check your internet connection and ensure the backend server is running.';
          } else {
            errorMsg = error.message;
          }
        }
      }
      
      // Create an error message
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'system',
        content: errorMsg,
        timestamp: new Date()
      };
      
      return {
        message: errorMessage,
        sessionId: sessionId || '',
        success: false,
        error: errorMsg
      };
    }
  }
  
  /**
   * Fetch message history for a session
   * @param sessionId The session ID to fetch history for
   * @returns A promise containing the message history
   */
  async getMessageHistory(sessionId: string): Promise<MessageHistoryResponse> {
    console.log(`MessageService: Fetching history for session ${sessionId}`);
    
    try {
      // Don't fetch for new chat sessions
      if (!sessionId || sessionId === NEW_CHAT_SESSION_ID) {
        return {
          messages: [],
          success: true
        };
      }
      
      // Fetch messages from the backend
      const response = await backendApi.getChatHistory(sessionId);
      
      if (response && response.messages) {
        // Process the messages to ensure they have the correct format
        const processedMessages = response.messages.map((msg: any) => ({
          ...msg,
          timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date()
        }));
        
        return {
          messages: processedMessages,
          success: true
        };
      }
      
      return {
        messages: [],
        success: true
      };
    } catch (error) {
      console.error("MessageService: Error fetching message history:", error);
      
      return {
        messages: [],
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch message history'
      };
    }
  }
  
  /**
   * Create a user message object
   * @param content The message content
   * @returns A Message object
   */
  createUserMessage(content: string): Message {
    return {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date()
    };
  }
  
  /**
   * Create a system message object
   * @param content The message content
   * @param messageType Optional message type for styling (default, info, warning, error, success)
   * @returns A Message object
   */
  createSystemMessage(content: string, messageType: string = 'default'): Message {
    return {
      id: this.generateMessageId(),
      role: 'system',
      content,
      timestamp: new Date(),
      messageType
    };
  }
  
  /**
   * Generate a unique message ID for system or client-generated messages
   * @returns A unique string ID
   */
  generateMessageId(): string {
    return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }
  
  /**
   * Fetches system message status from the dedicated API endpoint
   * This allows us to get operational status updates separate from the actual LLM responses
   * @param action The action to check status for (e.g., 'get_search_status')
   * @param sessionId The session ID to check status for
   * @param dispatch Redux dispatch function to update system messages in the store
   */
  async checkSystemMessageStatus(action: string, sessionId: string, dispatch: Function): Promise<void> {
    try {
      console.log(`MessageService: Checking system message status for ${action} in session ${sessionId}`);
      
      // Call the dedicated system message endpoint using our API client
      const response = await backendApi.getSystemMessage(action, sessionId);
      
      console.log('MessageService: System message status response:', response);
      
      // Process system messages if we received any
      if (response && response.messages && response.messages.length > 0) {
        response.messages.forEach((sysMsg: any) => {
          console.log(`MessageService: Processing system message: ${sysMsg.type} - ${sysMsg.content.substring(0, 30)}...`);
          
          const systemMessage: Message = {
            id: sysMsg.id || this.generateMessageId(),
            role: 'system',
            content: sysMsg.content || `System status: ${sysMsg.type}`,
            timestamp: sysMsg.timestamp ? new Date(sysMsg.timestamp) : new Date(),
            messageType: sysMsg.type || 'info',
            isSearchMessage: action === 'get_search_status'
          };
          
          // Add the system message to the store
          dispatch({
            type: 'ADD_SYSTEM_MESSAGE',
            payload: {
              sessionId: sessionId,
              message: systemMessage
            }
          });
        });
      }
    } catch (error) {
      console.error('MessageService: Error fetching system message status:', error);
      
      // Add an error message to the store
      const errorMessage = this.createSystemMessage(`Error checking ${action} status`, 'error');
      dispatch({
        type: 'ADD_SYSTEM_MESSAGE',
        payload: {
          sessionId: sessionId,
          message: errorMessage
        }
      });
    }
  }
  
  /**
   * Create a loading message object
   * @returns A Message object with loading state
   */
  createLoadingMessage(): Message {
    return {
      id: `loading-${Date.now()}`,
      role: 'assistant',
      content: 'Thinking...',
      timestamp: new Date(),
      isLoading: true
    };
  }
  
  // Search completion is now handled via system messages in the main response stream
  
  /**
   * Update system messages based on received updates
   * @param messages The current messages array
   * @param systemMessageId ID of the system message to update
   * @param systemMessageContent New content for the message
   * @param systemMessageStatus New status of the message
   * @returns Updated messages array if changes were made, null otherwise
   */
  private updateSystemMessage(messages: Message[], systemMessageId: string, systemMessageContent: string, systemMessageStatus: string): Message[] | null {
    console.log(`MessageService: Updating system message with ID: ${systemMessageId}, new status: ${systemMessageStatus}`);
    
    if (!systemMessageId) {
      return null;
    }
    
    let hasUpdates = false;
    
    // Map through messages to find and update the specific system message by ID
    const updatedMessages = messages.map(msg => {
      // Check if this is the system message we're looking for
      if (msg.id === systemMessageId) {
        console.log(`MessageService: Found system message to update: ${msg.id}`);
        
        // Determine the message type based on status
        let messageType = 'default';
        if (systemMessageStatus === 'active') messageType = 'info';
        if (systemMessageStatus === 'complete') messageType = 'success';
        if (systemMessageStatus === 'error') messageType = 'error';
        
        // Return updated message
        hasUpdates = true;
        return {
          ...msg,
          content: systemMessageContent,
          messageType: messageType
        };
      }
      
      // Return unchanged message
      return msg;
    });
    
    return hasUpdates ? updatedMessages : null;
  }
  
  /**
   * Create and send a message, handling all related business logic
   * @param messageContent The message content to send
   * @param sessionId The current session ID
   * @param dispatch Function to dispatch state updates
   * @param callbacks Callbacks for UI updates
   * @returns Promise that resolves when the message is sent
   */
  async createAndSendMessage(
    messageContent: string,
    sessionId: string,
    dispatch: (action: any) => void,
    callbacks: {
      setCurrentSessionId: (sessionId: string) => void;
      onNewChatPlaceholder: (tempId: string, initialTitle: string) => void;
      onConfirmNewChat: (tempId: string, realSessionData: { id: string; title: string }) => void;
      onFailedNewChat: (tempId: string) => void;
    }
  ): Promise<void> {
    // Don't process empty messages
    if (!messageContent || !messageContent.trim()) {
      console.log('MessageService: Empty message, not sending');
      return;
    }
    
    console.log('MessageService: Starting createAndSendMessage', { 
      sessionId, 
      messageContent: messageContent.substring(0, 30) + '...' 
    });
    
    // Create user message
    const userMessage = this.createUserMessage(messageContent);
    
    // Add user message to UI
    dispatch({
      type: 'ADD_USER_MESSAGE',
      payload: {
        sessionId: sessionId,
        message: userMessage
      }
    });
    
    // Create a loading message for immediate feedback
    const loadingMessage = this.createLoadingMessage();
    
    // Add loading message to UI
    dispatch({
      type: 'PROCESS_ASSISTANT_RESPONSE',
      payload: {
        sessionId: sessionId,
        loadingId: loadingMessage.id,
        assistantMessage: loadingMessage
      }
    });
    
    // Generate a temporary ID for new chats
    let tempId = '';
    
    if (sessionId === NEW_CHAT_SESSION_ID) {
      // Create a temporary chat placeholder for immediate UX
      tempId = `temp-${Date.now()}`;
      const initialTitle = this.generateTitle(messageContent);
      
      // Callback to show chat in UI
      callbacks.onNewChatPlaceholder(tempId, initialTitle);
    }
    
    try {
      // Send message to backend and handle immediate responses
      console.log(`MessageService: Sending message to backend, sessionId=${sessionId}`);
      let response = await this.sendMessage(messageContent, sessionId);
      
      // STAGE 2: MessageService receives the response from the API
      console.log(`STAGE 2 - MessageService received response:`, JSON.stringify(response));
      console.log(`STAGE 2 - Response keys:`, Object.keys(response));
      if (response.content) console.log(`STAGE 2 - Content field:`, response.content);
      if (response.message?.content) console.log(`STAGE 2 - Message.content field:`, response.message.content);
      
      // If we got a session ID from a new chat, update the frontend
      if (sessionId === NEW_CHAT_SESSION_ID && response.sessionId) {
        // Confirm the new chat and replace the placeholder
        console.log(`MessageService: Confirming new chat placeholder ${tempId} with real session ${response.sessionId}`);
        
        // Initialize session explicitly to ensure state is prepared for the new session ID
        dispatch({
          type: 'INITIALIZE_SESSION',
          payload: {
            temporarySessionId: NEW_CHAT_SESSION_ID,
            finalSessionId: response.sessionId
          }
        });
        
        // Change current session ID to the real one
        callbacks.setCurrentSessionId(response.sessionId);
        
        // Confirm the placeholder in UI
        callbacks.onConfirmNewChat(tempId, {
          id: response.sessionId,
          // Use a fallback for title if not provided
          title: response.title || this.generateTitle(messageContent)
        });
        
        // Update local sessionId for the rest of processing
        sessionId = response.sessionId;
      }
      
      // Directly log all properties on the response object
      console.log('Debug - Response keys:', Object.keys(response));
      
      // Use type assertion to allow string indexing
      const responseObj = response as Record<string, any>;
      for (const key of Object.keys(responseObj)) {
        console.log(`Debug - Response[${key}]:`, typeof responseObj[key] === 'object' ? 
          JSON.stringify(responseObj[key]) : responseObj[key]);
      }
      
      // Directly use the content field which we know is sent from the backend
      if (response.content && typeof response.content === 'string') {
        const finalContent = response.content;
        console.log('Using content field directly:', finalContent);
        
        // Create a proper message object
        const assistantMessage: Message = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: finalContent,
          timestamp: new Date(),
          isLoading: false
        };
        
        // Directly add the assistant message to the UI
        dispatch({
          type: 'PROCESS_ASSISTANT_RESPONSE',
          payload: {
            sessionId: response.sessionId || response.session_id || sessionId,
            loadingId: loadingMessage.id,
            assistantMessage: assistantMessage
          }
        });
      } else if (response.tier3 && typeof response.tier3 === 'string') {
        const finalContent = response.tier3;
        console.log('Using tier3 field directly:', finalContent);
        
        // Create a proper message object
        const assistantMessage: Message = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: finalContent,
          timestamp: new Date(),
          isLoading: false
        };
        
        // Directly add the assistant message to the UI
        dispatch({
          type: 'PROCESS_ASSISTANT_RESPONSE',
          payload: {
            sessionId: response.sessionId || response.session_id || sessionId,
            loadingId: loadingMessage.id,
            assistantMessage: assistantMessage
          }
        });
      } else if (response.message?.content && typeof response.message.content === 'string') {
        const finalContent = response.message.content;
        console.log('Using message.content field:', finalContent);
        
        // Create a proper message object
        const assistantMessage: Message = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: finalContent,
          timestamp: new Date(),
          isLoading: false
        };
        
        // Directly add the assistant message to the UI
        dispatch({
          type: 'PROCESS_ASSISTANT_RESPONSE',
          payload: {
            sessionId: response.sessionId || response.session_id || sessionId,
            loadingId: loadingMessage.id,
            assistantMessage: assistantMessage
          }
        });
      } else {
        const finalContent = 'No response received - Unable to extract content from backend response';
        console.error('Failed to extract content from response:', response);
        
        // Create a proper message object
        const assistantMessage: Message = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: finalContent,
          timestamp: new Date(),
          isLoading: false
        };
        
        // Directly add the assistant message to the UI
        dispatch({
          type: 'PROCESS_ASSISTANT_RESPONSE',
          payload: {
            sessionId: response.sessionId || response.session_id || sessionId,
            loadingId: loadingMessage.id,
            assistantMessage: assistantMessage
          }
        });
      }
      
    } catch (error) {
      console.error('Error in createAndSendMessage:', error);
      // Handle error
      this.handleMessageError(dispatch, sessionId, tempId, callbacks.onFailedNewChat);
    }
  }
  
  /**
   * Generate a title from a message
   * @param message The message to generate a title from
   * @returns A title string
   */
  private generateTitle(message: string): string {
    return message.substring(0, 30) + (message.length > 30 ? '...' : '');
  }
  
  /**
   * Handle message sending errors
   * @param dispatch Function to dispatch state updates
   * @param sessionId The current session ID
   * @param tempId The temporary ID for new chats
   * @param onFailedNewChat Callback for failed new chats
   */
  private handleMessageError(
    dispatch: (action: any) => void,
    sessionId: string,
    tempId: string,
    onFailedNewChat: (tempId: string) => void
  ): void {
    console.log('Handling message error for session:', sessionId);
    
    // First remove any loading indicators
    dispatch({
      type: 'REMOVE_LOADING_INDICATOR',
      payload: {
        sessionId: sessionId
      }
    });
    
    // Create an error message as a system message (not user message)
    const errorMessage: Message = {
      id: `sys-err-${Date.now()}`,
      role: 'system',
      content: 'Error sending message to backend.',
      timestamp: new Date(),
      messageType: 'error'
    };
    
    // Add as a system message
    dispatch({ 
      type: 'ADD_SYSTEM_MESSAGE', 
      payload: { 
        sessionId: sessionId, 
        message: errorMessage 
      } 
    });
    
    if (sessionId === NEW_CHAT_SESSION_ID && tempId) {
      onFailedNewChat(tempId);
    }
  }
}

// Export singleton instance
const messageService = new MessageService();
export default messageService;
