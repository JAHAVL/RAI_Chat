/**
 * System Message Service
 * Handles operations related to system messages
 * This service separates business logic from UI components.
 */

import { Message } from '../../api/backend_api_interface';
import backendApi from '../../api/backend_api_interface';

/**
 * Types of system messages that can be displayed
 */
export enum SystemMessageType {
  WELCOME = 'welcome',
  ERROR = 'error',
  INFO = 'info',
  WARNING = 'warning',
  SUCCESS = 'success',
  SEARCH = 'search'
}

/**
 * System Message Service class to handle all system message operations
 */
class SystemMessageService {
  /**
   * Create a system message
   * @param content The message content
   * @param type The type of system message
   * @returns A system message object
   */
  createSystemMessage(content: string, type: SystemMessageType = SystemMessageType.INFO): Message {
    return {
      id: `sys-${type}-${Date.now()}`,
      role: 'system',
      content,
      timestamp: new Date(),
      messageType: type
    };
  }

  /**
   * Create an error system message
   * @param content The error message content
   * @returns An error system message object
   */
  createErrorMessage(content: string): Message {
    return this.createSystemMessage(content, SystemMessageType.ERROR);
  }

  /**
   * Create a welcome system message
   * @param content The welcome message content
   * @returns A welcome system message object
   */
  createWelcomeMessage(content: string): Message {
    return this.createSystemMessage(content, SystemMessageType.WELCOME);
  }

  /**
   * Create a search-related system message
   * @param content The search message content
   * @returns A search system message object
   */
  createSearchMessage(content: string): Message {
    return {
      id: `sys-search-${Date.now()}`,
      role: 'system',
      content,
      timestamp: new Date(),
      messageType: SystemMessageType.SEARCH,
      isSearchMessage: true
    };
  }

  /**
   * Add a system message to a session
   * @param sessionId The session ID to add the message to
   * @param content The message content
   * @param type The type of system message
   * @param dispatch Function to dispatch state updates
   */
  addSystemMessage(
    sessionId: string,
    content: string,
    type: SystemMessageType = SystemMessageType.INFO,
    dispatch: (action: any) => void
  ): void {
    const message = this.createSystemMessage(content, type);
    
    dispatch({
      type: 'ADD_MESSAGE',
      payload: {
        sessionId,
        message
      }
    });
    
    // Also log that we would send to backend in future
    console.log(`Future feature: Would send system message to backend: ${content} (${type}) for session ${sessionId}`);
  }
  
  /**
   * Send a system message to the backend (future feature)
   * This method is prepared for the future architecture but doesn't affect current functionality
   */
  async sendSystemMessageToBackend(
    sessionId: string,
    content: string,
    type: SystemMessageType,
    relatedMessageId?: string
  ): Promise<void> {
    try {
      // This will just log the message for now
      await backendApi.createSystemMessage(
        sessionId,
        content,
        type.toString(),
        relatedMessageId
      );
    } catch (error) {
      console.error('Error sending system message to backend:', error);
    }
  }
  
  /**
   * Fetch system messages for a session from the backend (future feature)
   * This method is prepared for the future architecture but doesn't affect current functionality
   */
  async fetchSystemMessages(
    sessionId: string,
    dispatch: (action: any) => void
  ): Promise<void> {
    try {
      // This will just return an empty array for now
      await backendApi.getSystemMessages(sessionId);
      console.log(`Future feature: Would fetch system messages for session ${sessionId}`);
    } catch (error) {
      console.error('Error fetching system messages:', error);
    }
  }

  /**
   * Determine if a system message should be displayed
   * @param message The message to check
   * @returns Whether the message should be displayed
   */
  shouldDisplaySystemMessage(message: Message): boolean {
    // Hide initial system messages like the welcome message when there are other messages
    if (message.id === 'initial-system-message') {
      const timestamp = message.timestamp instanceof Date 
        ? message.timestamp.getTime() 
        : new Date(message.timestamp).getTime();
        
      if (timestamp < Date.now() - 60000) {
        return false;
      }
    }
    
    // Always show error messages
    if (message.messageType === SystemMessageType.ERROR) {
      return true;
    }
    
    // Always show search messages
    if (message.isSearchMessage) {
      return true;
    }
    
    return true;
  }
}

export default new SystemMessageService();
