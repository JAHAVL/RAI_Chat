/**
 * Session Service
 * Handles all session-related operations including creating, fetching, and deleting sessions.
 * This service separates business logic from UI components.
 */

import raiAPIClient, { Session } from '../../api/rai_api';
import { Message } from '../../api/rai_api';
import messageService from './messageService';

// Constants
export const NEW_CHAT_SESSION_ID = 'new_chat';

// Types
export interface SessionResponse {
  session: Session | null;
  success: boolean;
  error?: string;
}

export interface SessionsListResponse {
  sessions: Session[];
  success: boolean;
  error?: string;
}

/**
 * Session Service class to handle all session-related operations
 */
class SessionService {
  /**
   * Fetch all available sessions
   * @returns A promise containing the list of sessions
   */
  async fetchSessions(): Promise<SessionsListResponse> {
    console.log("SessionService: Fetching all sessions");
    
    try {
      const response = await raiAPIClient.getChatSessions();
      
      if (response && response.sessions) {
        return {
          sessions: response.sessions,
          success: true
        };
      }
      
      return {
        sessions: [],
        success: true
      };
    } catch (error) {
      console.error("SessionService: Error fetching sessions:", error);
      
      return {
        sessions: [],
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch sessions'
      };
    }
  }
  
  /**
   * Create a new session
   * @param title The title for the new session
   * @returns A promise containing the created session
   */
  async createSession(title: string): Promise<SessionResponse> {
    console.log(`SessionService: Creating new session with title: ${title}`);
    
    try {
      // Send a message to create a new session
      const response = await raiAPIClient.sendMessage({
        message: `Create new chat: ${title}`,
        sessionId: 'new_chat' // Use a string ID to create a new session
      });
      
      if (response && response.session_id) {
        const newSession: Session = {
          id: response.session_id,
          title: response.title || title,
          timestamp: new Date().toISOString(),
          last_modified: new Date().toISOString()
        };
        
        return {
          session: newSession,
          success: true
        };
      }
      
      return {
        session: null,
        success: false,
        error: 'Failed to create session - no session ID returned'
      };
    } catch (error) {
      console.error("SessionService: Error creating session:", error);
      
      return {
        session: null,
        success: false,
        error: error instanceof Error ? error.message : 'Failed to create session'
      };
    }
  }
  
  /**
   * Delete a session
   * @param sessionId The ID of the session to delete
   * @returns A promise indicating success or failure
   */
  async deleteSession(sessionId: string): Promise<{ success: boolean; error?: string }> {
    console.log(`SessionService: Deleting session: ${sessionId}`);
    
    try {
      const response = await raiAPIClient.deleteChatSession(sessionId);
      const success = response && typeof response === 'object' && response.status === 'success';
      
      return {
        success
      };
    } catch (error) {
      console.error("SessionService: Error deleting session:", error);
      
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to delete session'
      };
    }
  }
  
  /**
   * Create a placeholder session for optimistic UI updates
   * @param initialMessage The initial message content
   * @returns A placeholder session object
   */
  createPlaceholderSession(initialMessage: string): Session {
    const title = initialMessage.substring(0, 30) + (initialMessage.length > 30 ? '...' : '');
    const tempId = `temp-${Date.now()}`;
    
    return {
      id: tempId,
      title,
      timestamp: new Date().toISOString(),
      last_modified: new Date().toISOString()
    };
  }
  
  /**
   * Check if a session ID is for a new chat
   * @param sessionId The session ID to check
   * @returns True if it's a new chat session
   */
  isNewChatSession(sessionId: string | null): boolean {
    return sessionId === NEW_CHAT_SESSION_ID;
  }
  
  /**
   * Load messages for a session, fetching from backend if needed
   * @param sessionId The session ID to load messages for
   * @param currentMessages Current messages in the state for this session
   * @param dispatch Function to dispatch state updates
   * @returns Promise that resolves when messages are loaded
   */
  async loadSessionMessages(
    sessionId: string, 
    currentMessages: Message[] | undefined, 
    dispatch: (action: any) => void
  ): Promise<void> {
    // Don't fetch for new chat sessions
    if (!sessionId || sessionId === NEW_CHAT_SESSION_ID) {
      return;
    }

    // Check if we already have messages for this session in state
    if (currentMessages && currentMessages.length > 0) {
      return;
    }

    try {
      // Fetch message history using the message service
      const historyResponse = await messageService.getMessageHistory(sessionId);
      
      if (historyResponse.success && historyResponse.messages.length > 0) {
        // Update the state with the fetched messages
        dispatch({
          type: 'SET_MESSAGES',
          payload: {
            sessionId: sessionId,
            messages: historyResponse.messages
          }
        });
      }
    } catch (error) {
      console.error("Error loading message history:", error);
    }
  }

  /**
   * Select a session and handle loading its messages
   * @param sessionId The session ID to select
   * @param currentMessages Current messages in the state for this session
   * @param dispatch Function to dispatch state updates
   * @param initialSystemMessage The initial system message to use for new sessions
   * @param setCurrentSessionId Function to update the current session ID in the UI
   */
  async selectSession(
    sessionId: string,
    currentMessages: { [key: string]: Message[] | undefined },
    dispatch: (action: any) => void,
    initialSystemMessage: Message,
    setCurrentSessionId: (sessionId: string) => void
  ): Promise<void> {
    console.log(`SessionService: Selecting session: ${sessionId}`);

    // Handle new chat selection
    if (sessionId === NEW_CHAT_SESSION_ID) {
      console.log("SessionService: Selected 'New Chat'");
      
      // If 'New Chat' is selected, ensure the state reflects this
      if (!currentMessages[NEW_CHAT_SESSION_ID] || currentMessages[NEW_CHAT_SESSION_ID].length === 0) {
        dispatch({ 
          type: 'SET_MESSAGES', 
          payload: { 
            sessionId: NEW_CHAT_SESSION_ID, 
            messages: [initialSystemMessage] 
          } 
        });
      }
      
      setCurrentSessionId(NEW_CHAT_SESSION_ID);
      return;
    }

    // Load messages for existing session
    const messagesForSession = currentMessages[sessionId];
    
    if (!messagesForSession || messagesForSession.length === 0) {
      try {
        console.log(`SessionService: Fetching history for session ${sessionId}`);
        const history = await raiAPIClient.getChatHistory(sessionId);
        
        if (history && history.messages && Array.isArray(history.messages)) {
          console.log(`SessionService: History loaded with ${history.messages.length} messages`);
          
          // Ensure all messages have proper timestamps as Date objects
          const processedMessages = history.messages.map(msg => ({
            ...msg,
            timestamp: msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp)
          }));
          
          dispatch({ 
            type: 'SET_MESSAGES', 
            payload: { 
              sessionId, 
              messages: processedMessages 
            } 
          });
        } else {
          console.log(`SessionService: No messages found for session ${sessionId}`);
          dispatch({ 
            type: 'SET_MESSAGES', 
            payload: { 
              sessionId, 
              messages: [
                initialSystemMessage, 
                { 
                  id: 'err-hist', 
                  role: 'system', 
                  content: 'Could not load chat history.', 
                  timestamp: new Date() 
                }
              ] 
            } 
          });
        }
      } catch (error) {
        console.error("SessionService: Error fetching history:", error);
        dispatch({ 
          type: 'SET_MESSAGES', 
          payload: { 
            sessionId, 
            messages: [
              initialSystemMessage, 
              { 
                id: 'err-hist-catch', 
                role: 'system', 
                content: 'Error loading chat history.', 
                timestamp: new Date() 
              }
            ] 
          } 
        });
      }
    } else {
      console.log(`SessionService: Using cached messages for session ${sessionId}`);
    }
    
    // Set the selected session as active
    setCurrentSessionId(sessionId);
  }

  /**
   * Handle the deletion of a session
   * @param deletedSessionId The ID of the deleted session
   * @param currentSessionId The current active session ID
   * @param dispatch Function to dispatch state updates
   * @param initialSystemMessage The initial system message to use for new sessions
   * @param setCurrentSessionId Function to update the current session ID in the UI
   */
  handleSessionDeletion(
    deletedSessionId: string,
    currentSessionId: string,
    dispatch: (action: any) => void,
    initialSystemMessage: Message,
    setCurrentSessionId: (sessionId: string) => void
  ): void {
    console.log(`SessionService: Handling deletion of session: ${deletedSessionId}`);
    
    // If the deleted session was the active one, switch to 'new chat'
    if (currentSessionId === deletedSessionId) {
      // Ensure the 'new_chat' state exists with the initial message
      if (!dispatch) {
        console.error("SessionService: dispatch function is required for handleSessionDeletion");
        return;
      }
      
      dispatch({ 
        type: 'SET_MESSAGES', 
        payload: { 
          sessionId: NEW_CHAT_SESSION_ID, 
          messages: [initialSystemMessage] 
        } 
      });
      
      setCurrentSessionId(NEW_CHAT_SESSION_ID);
    }
    
    // Remove the deleted session's messages from state
    dispatch({ type: 'REMOVE_SESSION_MESSAGES', payload: deletedSessionId });
  }
  
  /**
   * Get chat history for a session
   * @param sessionId The ID of the session to get history for
   * @returns Promise with the chat history
   */
  async getChatHistory(sessionId: string): Promise<{ messages: Message[] }> {
    console.log(`SessionService: Getting chat history for session: ${sessionId}`);
    
    try {
      const response = await raiAPIClient.getChatHistory(sessionId);
      
      // Ensure we always return a messages array
      return {
        messages: response.messages || []
      };
    } catch (error) {
      console.error("SessionService: Error getting chat history:", error);
      // Return empty messages array on error
      return { messages: [] };
    }
  }
}

// Export singleton instance
const sessionService = new SessionService();
export default sessionService;
