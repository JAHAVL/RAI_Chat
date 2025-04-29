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
  | { type: 'SET_CURRENT_SESSION'; payload: SessionId }
  | { type: 'CLEAR_ALL_MESSAGES'; payload: SessionId };

export interface ChatContextType {
  state: ChatState;
  dispatch: React.Dispatch<ChatAction>;
  sendMessage: (message: string, sessionId: string) => Promise<string>;
  createNewChat: () => Promise<void>;
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
      
      console.log('INITIALIZE_SESSION - Starting', { 
        temporarySessionId, 
        finalSessionId,
        tempMessagesCount: state.messagesBySession[temporarySessionId]?.length || 0
      });
      
      // Special handling for new chat sessions
      if (temporarySessionId === NEW_CHAT_SESSION_ID) {
        console.log(`Initializing new chat session with ID: ${finalSessionId}`);
        
        // Get any existing messages from the temporary session
        const existingMessages = state.messagesBySession[temporarySessionId] || [];
        console.log(`Existing messages in temporary session: ${existingMessages.length}`);
        
        if (existingMessages.length > 0) {
          console.log(`Message details:`, JSON.stringify(existingMessages.map(m => ({ 
            id: m.id, 
            role: m.role,
            content: typeof m.content === 'string' ? m.content.substring(0, 20) : '[complex content]' 
          }))));
        }
        
        // For new chats, transfer any existing messages to the new session
        // This ensures messages sent while in "new_chat" mode appear in the final session
        const newMessagesBySession = {
          ...state.messagesBySession,
          [finalSessionId]: [...existingMessages] // Transfer existing messages
        };
        
        const newSystemMessagesBySession = {
          ...state.systemMessagesBySession,
          [finalSessionId]: state.systemMessagesBySession[temporarySessionId] || [] // Transfer system messages
        };
        
        // Create new state with all messages properly transferred
        const newState = {
          ...state,
          messagesBySession: newMessagesBySession,
          systemMessagesBySession: newSystemMessagesBySession,
          currentSessionId: finalSessionId
        };
        
        console.log('INITIALIZE_SESSION - Result', { 
          currentSessionId: newState.currentSessionId,
          finalMessagesCount: newState.messagesBySession[finalSessionId]?.length || 0
        });
        
        return newState;
      }
      
      // Normal session initialization for existing chats (non-new-chat)
      const messagesFromTempSession = state.messagesBySession[temporarySessionId] || [];
      const systemMessagesFromTempSession = state.systemMessagesBySession[temporarySessionId] || [];
      
      console.log(`Messages to transfer: ${messagesFromTempSession.length}`);
      
      // Create a copy of the state structures with both temporaryId messages and finalId references
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
      console.log(`STAGE 3 - Message content: ${typeof assistantMessage.content === 'string' ? 
                      assistantMessage.content.substring(0, 50) : 
                      JSON.stringify(assistantMessage.content).substring(0, 50)}...`);
      
      // Make sure we have a valid sessionId
      if (!sessionId) {
          console.error('PROCESS_ASSISTANT_RESPONSE: Missing sessionId');
          return state;
      }
      
      // Get current messages (or empty array if none)
      const currentMessagesBySession = { ...state.messagesBySession };
      
      // CRITICAL FIX: Look for NEW_CHAT_SESSION_ID and check if there are messages there
      // This handles the case where messages are still in the temporary session 
      // but we're processing in the new session
      const newChatMessages = currentMessagesBySession[NEW_CHAT_SESSION_ID] || [];
      if (sessionId !== NEW_CHAT_SESSION_ID && newChatMessages.length > 0 && 
          (currentMessagesBySession[sessionId]?.length === 0 || !currentMessagesBySession[sessionId])) {
        console.log(`WARNING: Found ${newChatMessages.length} messages in temp session that should be in ${sessionId}`);
        
        // Copy all messages from NEW_CHAT_SESSION_ID to this session
        currentMessagesBySession[sessionId] = [...newChatMessages];
        
        // Clear the temporary session to avoid duplicates
        delete currentMessagesBySession[NEW_CHAT_SESSION_ID];
      }
      
      // Now get messages for this session (which may have been updated above)
      const currentMessages = currentMessagesBySession[sessionId] || [];
      
      console.log(`PROCESS_ASSISTANT_RESPONSE for session ${sessionId}:`, 
                  `Current message count=${currentMessages.length}, ` +
                  `Message content: ${typeof assistantMessage.content === 'string' ? 
                      assistantMessage.content.substring(0, 50) : 
                      JSON.stringify(assistantMessage.content).substring(0, 50)}...`);
      
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
          
          // Make sure content is a string
          if (typeof assistantMessage.content !== 'string') {
              console.log(`Converting non-string content to string`, assistantMessage.content);
              assistantMessage.content = JSON.stringify(assistantMessage.content);
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
      // When switching to a new chat session, make sure it has the initial system message
      if (action.payload === NEW_CHAT_SESSION_ID && 
          (!state.messagesBySession[NEW_CHAT_SESSION_ID] || 
           state.messagesBySession[NEW_CHAT_SESSION_ID].length === 0)) {
        
        console.log('Initializing NEW_CHAT_SESSION_ID with welcome message');
        
        return {
          ...state,
          currentSessionId: action.payload,
          // Initialize with the welcome message for new chats
          messagesBySession: {
            ...state.messagesBySession,
            [NEW_CHAT_SESSION_ID]: [initialSystemMessage]
          }
        };
      }
      
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
    
    case 'CLEAR_ALL_MESSAGES': {
      const sessionId = action.payload;
      console.log(`Clearing all messages for session: ${sessionId}`);
      
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: [initialSystemMessage] // Reset to only the welcome message
        },
        systemMessagesBySession: {
          ...state.systemMessagesBySession,
          [sessionId]: [] // Reset system messages
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
  createNewChat: async () => {}, // Update return type to Promise<void>
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
  
  // Function to create a new chat session
  const createNewChat = useCallback(async (): Promise<void> => {
    console.log('Creating new chat...');
    
    // First, clear any existing messages to ensure a clean UI immediately
    dispatch({
      type: 'CLEAR_ALL_MESSAGES',
      payload: NEW_CHAT_SESSION_ID
    });
    
    // Update the UI to show we're creating a new chat
    dispatch({
      type: 'SET_CURRENT_SESSION',
      payload: NEW_CHAT_SESSION_ID
    });
    
    // That's it - we'll get the real session ID when the first message is sent
    return Promise.resolve();
  }, [dispatch]);
  
  // Function to set the current session
  const setCurrentSession = useCallback((sessionId: string) => {
    dispatch({
      type: 'SET_CURRENT_SESSION',
      payload: sessionId
    });
  }, []);
  
  // Function to send a message to the backend
  const sendMessage = useCallback(async (messageContent: string, sessionId: string) => {
    console.log(`SendMessage [START]: sessionId=${sessionId}, currentSession=${state.currentSessionId}`);
    
    try {
      // Check if this is a search query
      const searchPattern = /\[SEARCH:\s*(.+?)\s*\]/i;
      const searchMatch = messageContent.match(searchPattern);
      const isSearchQuery = !!searchMatch;
      
      // Create user message
      const userMessage = createUserMessage(messageContent);
      
      // Store original session ID for tracking
      const originalSessionId = sessionId;
      
      // Add user message to state immediately, so it's visible in the UI
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
      
      // Send the message to the backend - let it handle creating new sessions
      let response;
      try {
        const api = backendApiInterface;
        // Send flag for creating new session if needed
        const isNewChat = sessionId === NEW_CHAT_SESSION_ID;
        response = await api.sendMessage(
          sessionId, 
          messageContent,
          isNewChat ? { new_chat: true } : {}
        );
        console.log('Message API Response:', response);
        
        // If we got a new session ID back, update our state
        if (response.session_id && response.session_id !== sessionId) {
          console.log(`Got new session ID: ${response.session_id}, updating state...`);
          
          // Initialize the session with the new ID
          dispatch({
            type: 'INITIALIZE_SESSION',
            payload: {
              temporarySessionId: sessionId,
              finalSessionId: response.session_id
            }
          });
          
          // Update the current session
          dispatch({
            type: 'SET_CURRENT_SESSION',
            payload: response.session_id
          });
          
          // Update our local variable for subsequent processing
          sessionId = response.session_id;
        }
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
      if (isSearchQuery || response.type === 'search_start' || response.status === 'searching') {
        
        console.log('Handling search response:', response);
        
        // For search start or progress updates
        if (response.type === 'search_start' || response.status === 'searching') {
          // Create a search-specific message
          const searchMessage: Message = {
            id: `search-${Date.now()}`,
            role: 'system',
            content: response.content || (searchMatch ? `Searching for: ${searchMatch[1]}...` : `Searching...`),
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
          
          if (response.raw_results) {
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
          
          // Create search result message
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
      
      // Log the final session and message before dispatching
      console.log(`SendMessage: Final processing - Adding assistant response to session=${sessionId}`);
      console.log(`SendMessage: Current messages in this session: ${state.messagesBySession[sessionId]?.length || 0}`);
      
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

      // Double-check that messages exist in this session after processing
      setTimeout(() => {
        const currentSessionMessages = state.messagesBySession[sessionId] || [];
        const originalSessionMessages = state.messagesBySession[originalSessionId] || [];
        const messageCount = currentSessionMessages.length;
        console.log(`SendMessage: After processing - Session ${sessionId} has ${messageCount} messages`);
        
        // If we don't have messages in this session but do in the original, something went wrong
        if (messageCount === 0 && originalSessionMessages.length > 0) {
          console.warn(`SendMessage: Messages appear to be in wrong session! Copying from ${originalSessionId} to ${sessionId}`);
          
          // As a last resort, copy messages from original to new session
          dispatch({
            type: 'SET_MESSAGES',
            payload: {
              sessionId: sessionId,
              messages: [...originalSessionMessages]
            }
          });
        }
      }, 100);
      
      // Return final session ID
      const finalSessionId = response.session_id || sessionId;
      console.log(`SendMessage: Returning finalSessionId=${finalSessionId}`);
      return finalSessionId;
      
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
            sessionId: sessionId,
            loadingId: `loading-error-${Date.now()}`,
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
  }, [dispatch, state, createUserMessage, backendApiInterface, createNewChat]);
  
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
