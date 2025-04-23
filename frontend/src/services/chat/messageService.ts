/**
 * Message Service
 * Handles all message-related operations including sending, receiving, and formatting messages.
 * This service separates business logic from UI components.
 */

import raiAPIClient from '../../api/rai_api';
import type { Message } from '../../pages/Main_Chat_UI/chat';

// Constants
export const NEW_CHAT_SESSION_ID = 'new_chat';

// Types
export interface MessageResponse {
  message: Message;
  sessionId: string;
  success: boolean;
  error?: string;
  thinking?: boolean;
  status?: string;
  response?: string;
  systemMessageId?: string;
  systemMessageAction?: string;
  systemMessageStatus?: string;
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
      const response = await raiAPIClient.sendMessage({
        message,
        sessionId: session_id
      });
      
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
      const response = await raiAPIClient.getChatHistory(sessionId);
      
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
      const response = await raiAPIClient.getSystemMessage(action, sessionId);
      
      console.log('MessageService: System message status response:', response);
      
      // Process system messages if we received any
      if (response && response.messages && response.messages.length > 0) {
        // Convert each system message to our Message format and dispatch to the store
        response.messages.forEach((sysMsg: any) => {
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
    if (!messageContent.trim()) {
      return;
    }
    
    // Create user message
    const userMessage = this.createUserMessage(messageContent);
    
    // Add user message to state
    dispatch({ 
      type: 'ADD_USER_MESSAGE', 
      payload: { 
        sessionId: sessionId, 
        message: userMessage 
      } 
    });
    
    // Generate tempId for new chats
    const tempId = sessionId === NEW_CHAT_SESSION_ID ? `temp-${Date.now()}` : '';
    
    // Handle new chat placeholder
    if (sessionId === NEW_CHAT_SESSION_ID) {
      const initialTitle = this.generateTitle(messageContent);
      callbacks.onNewChatPlaceholder(tempId, initialTitle);
    }
    
    try {
      // Add the loading message first to show feedback to the user
      const loadingMessage = this.createLoadingMessage();
      dispatch({
        type: 'PROCESS_ASSISTANT_RESPONSE',
        payload: {
          sessionId: sessionId,
          loadingId: loadingMessage.id,
          assistantMessage: loadingMessage
        }
      });
      
      // Send message to backend and handle immediate responses
      console.log(`MessageService: Sending message to backend: ${messageContent.substring(0, 50)}...`);
      let response = await this.sendMessage(messageContent, sessionId);
      console.log('MessageService: Response from backend:', 
                 JSON.stringify(response).substring(0, 200), '...');
                 
      // Handle the case where the backend indicates we should continue waiting
      // for a follow-up response (typically after a web search completes)
      if (response.continueWaitingForResponse) {
        console.log('MessageService: Received continueWaitingForResponse flag, waiting for final LLM response');
        
        // We received a system message (like "search complete"), but we expect a follow-up
        // message with the actual LLM response. Let's fetch that now.
        try {
          // For now, just show the system message in the UI
          if (response.message) {
            dispatch({
              type: 'ADD_SYSTEM_MESSAGE',
              payload: {
                sessionId: sessionId,
                message: response.message
              }
            });
          }
          
          // But we also wait for another response with the actual results
          // The backend should send the final LLM response after the search_complete message
          console.log('MessageService: Awaiting final LLM response after search completion...');
          
          // First, let's check the system message status from our dedicated endpoint
          await this.checkSystemMessageStatus('get_search_status', sessionId, dispatch);
          
          // Then we send an empty message but with a flag to indicate we're just waiting for results
          response = await this.sendMessage('', sessionId);
          console.log('MessageService: Received final LLM response:', 
                     JSON.stringify(response).substring(0, 200), '...');
        } catch (error) {
          console.error('MessageService: Error waiting for final response:', error);
        }
      }
      
      // Handle system messages and continue processing for assistant response
      if (response.success && response.systemMessageAction && response.systemMessageStatus) {
        console.log(`MessageService: Handling system message: ${response.systemMessageAction}, status: ${response.systemMessageStatus}`);
        
        // When we get a system message, don't also process it as an assistant response
        // Only add it as a system message, not as part of the conversation
        if (response.systemMessageId) {
          const getMessagesPayload = { sessionId: response.sessionId || sessionId };
          
          try {
            // Get system messages safely with proper fallbacks
            const systemMessages = (dispatch({ 
              type: 'GET_SYSTEM_MESSAGES', 
              payload: getMessagesPayload 
            }) as unknown as Record<string, Message[]>) || {};
            
            const sessId = response.sessionId || sessionId;
            const currentSystemMessages = systemMessages && systemMessages[sessId] ? systemMessages[sessId] : [];
            const existingMessage = currentSystemMessages.find(msg => msg.id === response.systemMessageId);
            
            if (existingMessage) {
              // Update the existing system message instead of adding a new one
              console.log(`MessageService: Updating existing system message with ID: ${response.systemMessageId}`);
              dispatch({
                type: 'UPDATE_SYSTEM_MESSAGE',
                payload: {
                  sessionId: response.sessionId || sessionId,
                  systemMessageId: response.systemMessageId,
                  message: response.message
                }
              });
              
              // Early return to avoid processing system message as an assistant message
              return;
            } else {
              // Add the system message to the UI if it doesn't exist already
              dispatch({
                type: 'ADD_SYSTEM_MESSAGE',
                payload: {
                  sessionId: response.sessionId || sessionId,
                  message: response.message
                }
              });
              
              // For web search 'active' status we want to return, but for 'complete'
              // we want to continue and show the final answer
              if (response.systemMessageAction === 'web_search') {
                if (response.systemMessageStatus === 'active') {
                  // Only return for active status (searching), but let the complete status go through
                  console.log('MessageService: Web search active, returning early');
                  return;
                } else if (response.systemMessageStatus === 'complete') {
                  // When search is complete, don't return - continue to process the assistant response
                  console.log('MessageService: Web search complete, will continue to show final answer');
                  // Don't return here so we continue to process the final answer from the LLM
                } else if (response.systemMessageStatus === 'error') {
                  // For error status, show the error but don't show final answer (since there isn't one)
                  console.log('MessageService: Web search error, returning early');
                  return;
                }
              }
            }
          } catch (error) {
            console.error('Error handling system message:', error);
            // Continue with normal message processing if system message handling fails
          }
        }
      }
      
      if (response.success) {
        // First remove any loading indicators
        dispatch({
          type: 'REMOVE_LOADING_INDICATOR',
          payload: {
            sessionId: response.sessionId || sessionId
          }
        });
        
        // Handle new chat session creation
        if (sessionId === NEW_CHAT_SESSION_ID && response.sessionId && response.sessionId !== NEW_CHAT_SESSION_ID) {
          // Update session state
          dispatch({
            type: 'INITIALIZE_SESSION',
            payload: {
              temporarySessionId: NEW_CHAT_SESSION_ID,
              finalSessionId: response.sessionId
            }
          });
          
          // Update current session ID
          callbacks.setCurrentSessionId(response.sessionId);
          
          // Confirm new chat in UI
          callbacks.onConfirmNewChat(tempId, { 
            id: response.sessionId, 
            title: this.generateTitle(messageContent)
          });
        }

        // Always try to show the final answer
        // Check all possible sources for content to avoid truncation
        // Order of preference: response.message.content > tier1 > response string
        let finalContent = '';
        let source = 'none';

        console.log('MessageService: Response analysis:', {
          hasMessageContent: Boolean(response.message?.content),
          messageContentLength: response.message?.content?.length || 0,
          hasTier1: Boolean(response.llm_response?.response_tiers?.tier1),
          tier1Length: response.llm_response?.response_tiers?.tier1?.length || 0,
          hasTier3: Boolean(response.llm_response?.response_tiers?.tier3),
          tier3Length: response.llm_response?.response_tiers?.tier3?.length || 0,
          hasResponseString: Boolean(response.response),
          responseStringLength: response.response?.length || 0
        });

        // Try to extract content from various sources in order of preference
        // Always prioritize tier3 if available
        if (response.llm_response?.response_tiers?.tier3) {
          finalContent = response.llm_response.response_tiers.tier3;
          source = 'llm_response.response_tiers.tier3';
        } else if (response.message?.content) {
          finalContent = response.message.content;
          source = 'message.content';
        } else if (response.llm_response?.response_tiers?.tier1) {
          finalContent = response.llm_response.response_tiers.tier1;
          source = 'llm_response.response_tiers.tier1';
        } else if (response.response) {
          finalContent = response.response;
          source = 'response';
        }

        // Log what we found and which source we're using
        console.log(`MessageService: Using content from '${source}' source, length: ${finalContent.length}`);
        if (finalContent.length > 0) {
          const last100 = finalContent.length > 100 ? finalContent.slice(-100) : finalContent;
          console.log(`MessageService: Final content last 100 chars: ...${last100}`);
        }

        if (finalContent) {
          // Create a proper message object
          const assistantMessage: Message = {
            id: `asst-${Date.now()}`,
            role: 'assistant',
            content: finalContent,
            timestamp: new Date(),
            isLoading: false
          };
          
          // Add the assistant message to the UI
          dispatch({
            type: 'PROCESS_ASSISTANT_RESPONSE',
            payload: {
              sessionId: response.sessionId || sessionId,
              loadingId: loadingMessage.id,
              assistantMessage: assistantMessage
            }
          });
        } else {
          console.log('MessageService: No content found to display as assistant message');
        }  
      } else {
        // Handle error
        this.handleMessageError(dispatch, sessionId, tempId, callbacks.onFailedNewChat);
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
