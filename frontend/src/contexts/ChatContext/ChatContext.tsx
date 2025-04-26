import React, { createContext, useContext, useReducer, useCallback } from 'react';
import type { Message } from '../../api/backend_api_interface';
import backendApiInterface from '../../api/backend_api_interface';

// --- Constants ---
export const NEW_CHAT_SESSION_ID = 'new_chat';

// --- Type Definitions ---
export type SessionId = string;

export type MessagesBySession = {
  [key: SessionId]: Message[];
};

export interface ChatState {
  messagesBySession: Partial<MessagesBySession>;
  systemMessagesBySession: Partial<MessagesBySession>;
  currentSessionId: string | null;
}

export type ChatAction =
  | { type: 'ADD_USER_MESSAGE'; payload: { sessionId: SessionId; message: Message } }
  | { type: 'ADD_LOADING_MESSAGE'; payload: { sessionId: SessionId; loadingId: string } }
  | { type: 'INITIALIZE_SESSION'; payload: { temporarySessionId: SessionId; finalSessionId: SessionId } } 
  | { type: 'PROCESS_ASSISTANT_RESPONSE'; payload: { sessionId: SessionId; loadingId: string; assistantMessage: Message; originalContent?: string } } 
  | { type: 'SET_MESSAGES'; payload: { sessionId: SessionId; messages: Message[] } }
  | { type: 'REMOVE_MESSAGE'; payload: { sessionId: SessionId; messageId: string } }
  | { type: 'REMOVE_LOADING_INDICATOR'; payload: { sessionId: SessionId } }
  | { type: 'ADD_SYSTEM_MESSAGE'; payload: { sessionId: SessionId; message: Message } }
  | { type: 'UPDATE_SYSTEM_MESSAGE'; payload: { sessionId: SessionId; systemMessageId: string; message: Message } }
  | { type: 'SET_CURRENT_SESSION'; payload: SessionId };

export interface ChatContextType {
  state: ChatState;
  dispatch: React.Dispatch<ChatAction>;
  sendMessage: (message: string, sessionId: string) => Promise<string>;
  createNewChat: () => void;
  setCurrentSession: (sessionId: string) => void;
}

// Initial system message shown when starting a new chat
export const initialSystemMessage: Message = { 
  id: 'sys-initial', 
  role: 'system', 
  content: 'Hi, I\'m R.ai. How can I help?', 
  timestamp: new Date() 
};

// Initial state for the chat context
const initialState: ChatState = {
  messagesBySession: { [NEW_CHAT_SESSION_ID]: [initialSystemMessage] },
  systemMessagesBySession: { [NEW_CHAT_SESSION_ID]: [] },
  currentSessionId: NEW_CHAT_SESSION_ID
};

// The reducer function that was previously in App.tsx
function chatReducer(state: ChatState, action: ChatAction): ChatState {
  console.log(`ChatReducer Action: ${action.type}, Payload:`, action.payload);

  switch (action.type) {
    case 'ADD_USER_MESSAGE': {
      const { sessionId, message } = action.payload;
      const currentMessages = state.messagesBySession[sessionId] || [];
      
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: [...currentMessages, message]
        }
      };
    }
    
    case 'ADD_LOADING_MESSAGE': {
      const { sessionId, loadingId } = action.payload;
      const currentMessages = state.messagesBySession[sessionId] || [];
      
      // Create a loading message
      const loadingMessage: Message = {
        id: loadingId,
        role: 'assistant',
        content: 'Thinking...',
        timestamp: new Date(),
        isLoading: true
      };
      
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: [...currentMessages, loadingMessage]
        }
      };
    }
    
    case 'INITIALIZE_SESSION': {
      const { temporarySessionId, finalSessionId } = action.payload;
      
      // Get existing messages and system messages
      const messagesFromTempSession = state.messagesBySession[temporarySessionId] || [];
      const systemMessagesFromTempSession = state.systemMessagesBySession[temporarySessionId] || [];
      
      console.log(`Messages to transfer: ${messagesFromTempSession.length}`);
      
      // Create a copy of the state structures with both temporaryId messages and finalId references
      // This is critical - we need to have both the old and new references for a consistent state
      const newMessagesBySession = {
        ...state.messagesBySession,
        [finalSessionId]: [...messagesFromTempSession] // Ensure we clone the array
      };
      
      const newSystemMessagesBySession = {
        ...state.systemMessagesBySession,
        [finalSessionId]: [...systemMessagesFromTempSession] // Ensure we clone the array
      };
      
      console.log(`INITIALIZE_SESSION: Created message list for ${finalSessionId} with ${newMessagesBySession[finalSessionId]?.length || 0} messages`);
      
      return {
        ...state,
        messagesBySession: newMessagesBySession,
        systemMessagesBySession: newSystemMessagesBySession,
        currentSessionId: finalSessionId // Update current session ID to the real one
      };
    }
    
    case 'PROCESS_ASSISTANT_RESPONSE': {
      const { sessionId, loadingId, assistantMessage, originalContent } = action.payload;
      
      // STAGE 3: App reducer processing the message for state update
      console.log(`STAGE 3 - Reducer processing assistant message:`);
      console.log(`STAGE 3 - Session ID: ${sessionId}`);
      console.log(`STAGE 3 - Assistant Message:`, JSON.stringify(assistantMessage));
      console.log(`STAGE 3 - Message content:`, assistantMessage.content);
      
      // Make sure we have a valid sessionId
      if (!sessionId) {
          console.error('PROCESS_ASSISTANT_RESPONSE: Missing sessionId');
          return state;
      }
      
      // Get current messages (or empty array if none)
      const currentMessagesBySession = { ...state.messagesBySession };
      const currentMessages = currentMessagesBySession[sessionId] || [];
      
      console.log(`PROCESS_ASSISTANT_RESPONSE for session ${sessionId}:`, 
                  `Current message count=${currentMessages.length}, ` +
                  `Message content: ${assistantMessage.content.substring(0, 50)}...`);
      
      // Handle loading messages vs. real messages
      const updatedMessages = [...currentMessages];
      
      // If this is a loading message, just add it
      if (assistantMessage.isLoading) {
          console.log(`Adding loading message to session ${sessionId}`);
          updatedMessages.push(assistantMessage);
      } else {
          // Check if the content is "No response received" but we have original content
          if (assistantMessage.content === 'No response received' && originalContent) {
              console.log(`Fixing 'No response received' with original content:`, originalContent);
              assistantMessage.content = originalContent;
          }
          
          // This is a real assistant message - find and replace loading message
          const loadingMsgIndex = updatedMessages.findIndex(msg => 
              msg.id === loadingId || (msg.role === 'assistant' && msg.isLoading));
          
          if (loadingMsgIndex >= 0) {
              // Replace loading message with real content
              console.log(`Replacing loading message at index ${loadingMsgIndex}`);
              updatedMessages[loadingMsgIndex] = assistantMessage;
          } else {
              // No loading message found, just add this one
              console.log(`No loading message found, adding new message`);
              updatedMessages.push(assistantMessage);
          }
      }
      
      // Update the state with our modified messages
      return {
          ...state,
          messagesBySession: {
              ...currentMessagesBySession,
              [sessionId]: updatedMessages
          }
      };
    }
    
    case 'SET_MESSAGES': {
      const { sessionId, messages } = action.payload;
      
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: messages
        }
      };
    }
    
    case 'REMOVE_MESSAGE': {
      const { sessionId, messageId } = action.payload;
      const currentMessages = state.messagesBySession[sessionId] || [];
      
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: currentMessages.filter(msg => msg.id !== messageId)
        }
      };
    }
    
    case 'ADD_SYSTEM_MESSAGE': {
      const { sessionId, message } = action.payload;
      const currentSystemMessages = state.systemMessagesBySession[sessionId] || [];
      
      return {
        ...state,
        systemMessagesBySession: {
          ...state.systemMessagesBySession,
          [sessionId]: [...currentSystemMessages, message]
        }
      };
    }
    
    case 'UPDATE_SYSTEM_MESSAGE': {
      const { sessionId, systemMessageId, message } = action.payload;
      const currentSystemMessages = state.systemMessagesBySession[sessionId] || [];
      
      return {
        ...state,
        systemMessagesBySession: {
          ...state.systemMessagesBySession,
          [sessionId]: currentSystemMessages.map(msg => 
            msg.id === systemMessageId ? message : msg
          )
        }
      };
    }
    
    case 'SET_CURRENT_SESSION': {
      return {
        ...state,
        currentSessionId: action.payload
      };
    }
    
    case 'REMOVE_LOADING_INDICATOR': {
      const { sessionId } = action.payload;
      const currentMessages = state.messagesBySession[sessionId] || [];
      
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: currentMessages.filter(msg => !msg.isLoading)
        }
      };
    }
    
    default:
      console.log(`Unknown action type: ${(action as any)?.type}`);
      return state;
  }
}

// Create the context with a default value
const defaultContextValue: ChatContextType = {
  state: initialState,
  dispatch: () => {},
  sendMessage: async () => { return ''; }, 
  createNewChat: () => {},
  setCurrentSession: () => {}
};

const ChatContext = createContext<ChatContextType>(defaultContextValue);

// Hook for components to use the chat context
export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

// Create a custom loading message
function createLoadingMessage(): Message {
  return {
    id: `loading-${Date.now()}`,
    role: 'assistant',
    content: 'Thinking...',
    timestamp: new Date(),
    isLoading: true
  };
}

// Create a user message
function createUserMessage(content: string): Message {
  return {
    id: `user-${Date.now()}`,
    role: 'user',
    content,
    timestamp: new Date()
  };
}

// The provider component that will wrap the app
export const ChatProvider: React.FC<{
  children: React.ReactNode;
  apiUrl?: string;
}> = ({ children, apiUrl }) => {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  
  // Function to create a new chat
  const createNewChat = useCallback(() => {
    dispatch({
      type: 'SET_CURRENT_SESSION',
      payload: NEW_CHAT_SESSION_ID
    });
  }, []);
  
  // Function to set the current session
  const setCurrentSession = useCallback((sessionId: string) => {
    dispatch({
      type: 'SET_CURRENT_SESSION',
      payload: sessionId
    });
  }, []);
  
  // Function to send a message to the backend
  const sendMessage = useCallback(async (messageContent: string, sessionId: string) => {
    try {
      // Check if this is a search query
      const searchPattern = /\[SEARCH:\s*(.+?)\s*\]/i;
      const searchMatch = messageContent.match(searchPattern);
      const isSearchQuery = !!searchMatch;
      
      // Create user message
      const userMessage = createUserMessage(messageContent);
      
      // Add user message to state
      dispatch({
        type: 'ADD_USER_MESSAGE',
        payload: {
          sessionId,
          message: userMessage
        }
      });
      
      // Create loading message ID
      const loadingId = `loading-${Date.now()}`;
      
      // Add loading indicator
      dispatch({
        type: 'ADD_LOADING_MESSAGE',
        payload: {
          sessionId,
          loadingId
        }
      });
      
      // Create a temporary ID for new chats
      let tempSessionId = '';
      if (sessionId === NEW_CHAT_SESSION_ID) {
        tempSessionId = `temp-${Date.now()}`;
      }
      
      // Send the message to the backend
      let response;
      try {
        const api = backendApiInterface;
        response = await api.sendMessage(sessionId, messageContent);
        console.log('Message API Response:', response);
      } catch (apiError) {
        console.error('API Error:', apiError);
        
        // Create an error message for API errors
        const assistantMessage: Message = {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content: `Sorry, I'm having trouble connecting to the server. Please try again later.`,
          timestamp: new Date(),
          messageType: 'error'
        };
        
        // Replace loading message with error message
        dispatch({
          type: 'PROCESS_ASSISTANT_RESPONSE',
          payload: {
            sessionId,
            loadingId,
            assistantMessage,
            originalContent: "Server connection error"
          }
        });
        
        return sessionId; // Return original session ID since we couldn't get a new one
      }
      
      // Handle search-specific responses
      if (isSearchQuery || (response && (
          response.type === 'search_start' || 
          response.type === 'search_results' ||
          response.action === 'web_search' || 
          response.status === 'searching' || 
          response.status === 'search_error'))) {
        
        console.log('Handling search response:', response);
        
        // For search start or progress updates
        if (response.type === 'search_start' || response.status === 'searching') {
          // Create a search-specific message
          const searchMessage: Message = {
            id: `search-${Date.now()}`,
            role: 'system',
            content: response.content || `Searching for: ${searchMatch ? searchMatch[1] : messageContent}...`,
            timestamp: new Date(),
            messageType: 'info',
            isSearchMessage: true
          };
          
          // Replace loading indicator with search message
          dispatch({
            type: 'PROCESS_ASSISTANT_RESPONSE',
            payload: {
              sessionId,
              loadingId,
              assistantMessage: searchMessage,
              originalContent: searchMessage.content
            }
          });
          
          return sessionId;
        }
        
        // For search results
        if (response.type === 'search_results') {
          let content = '';
          
          if (response.content) {
            content = response.content;
          } else if (response.raw_results) {
            // Format raw results if available
            content = 'Search results:\n\n';
            try {
              const results = Array.isArray(response.raw_results) ? response.raw_results : [response.raw_results];
              content += results.map((result: any, index: number) => 
                `${index + 1}. **${result.title || 'No title'}**\n${result.url || 'No URL'}\n${result.snippet || 'No description'}\n`
              ).join('\n');
            } catch (e) {
              console.error('Error formatting search results:', e);
              content = `Search results available but could not be formatted: ${JSON.stringify(response.raw_results).substring(0, 100)}...`;
            }
          } else {
            content = 'Search complete, but no results were found.';
          }
          
          // Create a search result message
          const resultMessage: Message = {
            id: `search-result-${Date.now()}`,
            role: 'assistant',
            content: content,
            timestamp: new Date(),
            messageType: response.status === 'error' ? 'error' : 'success',
            isSearchMessage: true
          };
          
          // Replace loading indicator with result message
          dispatch({
            type: 'PROCESS_ASSISTANT_RESPONSE',
            payload: {
              sessionId,
              loadingId,
              assistantMessage: resultMessage,
              originalContent: content
            }
          });
          
          return sessionId;
        }
      }
      
      // If this is a new chat and we received a real session ID, initialize the session
      if (sessionId === NEW_CHAT_SESSION_ID && response.session_id) {
        console.log(`Initializing session from temporary to real: ${response.session_id}`);
        
        dispatch({
          type: 'INITIALIZE_SESSION',
          payload: {
            temporarySessionId: NEW_CHAT_SESSION_ID,
            finalSessionId: response.session_id
          }
        });
        
        // Update the session ID for subsequent processing
        sessionId = response.session_id;
      }
      
      // Extract the content from the response
      let responseContent = '';
      
      if (response.content) {
        responseContent = response.content;
        console.log('Using content field:', responseContent);
      } else if (response.tier3) {
        responseContent = response.tier3;
        console.log('Using tier3 field:', responseContent);
      } else if (response.message?.content) {
        responseContent = response.message.content;
        console.log('Using message.content field:', responseContent);
      } else if (response.status === 'error') {
        responseContent = `Error: ${response.response || 'Unknown server error'}`;
        console.error('Error response from server:', response);
      } else {
        responseContent = 'No response received';
        console.error('No content found in response:', response);
      }
      
      // Create assistant message
      const assistantMessage: Message = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: responseContent,
        timestamp: new Date(),
        messageType: response.status === 'error' ? 'error' : 'normal'
      };
      
      // Add assistant message to state
      dispatch({
        type: 'PROCESS_ASSISTANT_RESPONSE',
        payload: {
          sessionId,
          loadingId,
          assistantMessage,
          originalContent: responseContent
        }
      });
      
      return response.session_id || sessionId;
      
    } catch (error) {
      console.error('Error in sendMessage flow:', error);
      
      // Create an error message
      const errorMessage: Message = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: `Sorry, something went wrong. Please try again. (${error instanceof Error ? error.message : 'Unknown error'})`,
        timestamp: new Date(),
        messageType: 'error'
      };
      
      try {
        // Always attempt to replace the loading message with our error message
        dispatch({
          type: 'PROCESS_ASSISTANT_RESPONSE',
          payload: {
            sessionId,
            loadingId: `loading-${Date.now() - 1000}`, // Create a fallback ID in case the original was lost
            assistantMessage: errorMessage,
            originalContent: errorMessage.content
          }
        });
      } catch (dispatchError) {
        console.error('Error dispatching error message:', dispatchError);
        
        // Last-ditch effort - just try to remove loading indicators
        dispatch({
          type: 'REMOVE_LOADING_INDICATOR',
          payload: {
            sessionId
          }
        });
      }
      
      return sessionId; // Return original session ID
    }
  }, []);
  
  return (
    <ChatContext.Provider value={{ 
      state, 
      dispatch, 
      sendMessage, 
      createNewChat, 
      setCurrentSession 
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export default ChatContext;
