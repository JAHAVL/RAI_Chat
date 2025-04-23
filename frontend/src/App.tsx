import React, { useState, useRef, useEffect, useContext, useReducer } from 'react';
import { ThemeProvider } from 'styled-components';
import { theme } from '../shared/theme'; // Corrected path to shared theme file
import { GlobalStyle } from './AppLayout'; // Import GlobalStyle
import ChatLibrary from './modules/chat_library/ChatLibrary';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import type { Message } from './pages/Main_Chat_UI/chat';
import AuthPage from './pages/Login_Page/AuthPage';
import raiAPIClient from './api/rai_api';
import { FaCode, FaVideo } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import ChatPage from './pages/Main_Chat_UI/ChatPage';
import AppRouter from './router';
import appInitService from './services/AppInitService';

// --- Constants ---
export const NEW_CHAT_SESSION_ID = 'new_chat';

// --- Type Definitions ---

export type SessionId = string;
type MessagesBySession = {
  [key: SessionId]: Message[];
};

interface AppState {
  messagesBySession: Partial<MessagesBySession>;
  systemMessagesBySession: Partial<MessagesBySession>;
  activeModule: string | null;
  loading: boolean;
  currentSessionId: string | null;
}

type AppAction =
  | { type: 'ADD_USER_MESSAGE'; payload: { sessionId: SessionId; message: Message } }
  | { type: 'ADD_LOADING_MESSAGE'; payload: { sessionId: SessionId; loadingId: string } }
  | { type: 'INITIALIZE_SESSION'; payload: { temporarySessionId: SessionId; finalSessionId: SessionId } } 
  | { type: 'PROCESS_ASSISTANT_RESPONSE'; payload: { sessionId: SessionId; loadingId: string; assistantMessage: Message } } 
  | { type: 'SET_MESSAGES'; payload: { sessionId: SessionId; messages: Message[] } }
  | { type: 'REMOVE_MESSAGE'; payload: { sessionId: SessionId; messageId: string } }
  | { type: 'REMOVE_LOADING_INDICATOR'; payload: { sessionId: SessionId } }
  | { type: 'SET_ACTIVE_MODULE'; payload: string | null }
  | { type: 'ADD_SYSTEM_MESSAGE'; payload: { sessionId: SessionId; message: Message } }
  | { type: 'UPDATE_SYSTEM_MESSAGE'; payload: { sessionId: SessionId; systemMessageId: string; message: Message } };

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}

interface AppContentProps {
  currentSessionId: SessionId; // Now always string
  setCurrentSessionId: React.Dispatch<React.SetStateAction<SessionId>>; // Now always string
  onNewSessionCreated: () => void;
  onNewChatPlaceholder: (tempId: string, initialTitle: string) => void;
  onConfirmNewChat: (tempId: string, realSessionData: { id: string; title: string }) => void;
  onFailedNewChat: (tempId: string) => void;
}

interface ModuleButtonProps {
  $active?: boolean;
}

export interface ChatLibraryRefMethods {
    addPlaceholder: (tempId: string, initialTitle: string) => void;
    confirmPlaceholder: (tempId: string, realSessionData: { id: string; title: string }) => void;
    removePlaceholder: (tempId: string) => void;
    fetchSessions: () => void;
}



export const initialSystemMessage: Message = { id: 'sys-initial', role: 'system', content: 'Hi, I\'m R.ai. How can I help?', timestamp: new Date() };

const initialState: AppState = {
  messagesBySession: { [NEW_CHAT_SESSION_ID]: [initialSystemMessage] },
  systemMessagesBySession: { [NEW_CHAT_SESSION_ID]: [] },
  activeModule: null,
  loading: false,
  currentSessionId: NEW_CHAT_SESSION_ID
};

function appReducer(state: AppState, action: AppAction): AppState {
  // Use logTrace for file logging via IPC, fallback to console.log
  const log = console.log; // Use console.log for web
  log(`Reducer Action: ${action.type}, Payload: ${JSON.stringify(action.payload)}`);

  switch (action.type) {
    case 'ADD_USER_MESSAGE': {
        const { sessionId, message } = action.payload;
        let currentMessages = state.messagesBySession?.[sessionId] || [];
        let nextMessagesBySession = { ...state.messagesBySession };

        // Always append the message (user or assistant role)
        // The special logic for initializing a new session's message list
        // is handled correctly within PROCESS_ASSISTANT_RESPONSE.
        currentMessages = [...currentMessages, message];

        nextMessagesBySession[sessionId] = currentMessages;

        // If this message confirms a NEW_CHAT_SESSION_ID, remove the placeholder entry
        if (sessionId !== NEW_CHAT_SESSION_ID && state.messagesBySession[NEW_CHAT_SESSION_ID]) {
             delete nextMessagesBySession[NEW_CHAT_SESSION_ID];
             log(`Reducer ADD_USER_MESSAGE: Removed placeholder ${NEW_CHAT_SESSION_ID}`);
        }


        const newState: AppState = {
            ...state,
            messagesBySession: nextMessagesBySession
        };
        log(`Reducer State After ADD_USER_MESSAGE for ${sessionId}: Messages count = ${newState.messagesBySession[sessionId]?.length}`);
        return newState;
    }
    case 'ADD_LOADING_MESSAGE': { // Adds loading indicator
        const { sessionId, loadingId } = action.payload;
        const currentMessages = state.messagesBySession?.[sessionId] || [];
        const hasLoading = currentMessages.some(msg => msg.isLoading);
        if (hasLoading) {
            log(`Reducer ADD_LOADING_MESSAGE: Loading already exists for ${sessionId}, skipping.`);
            return state; // Prevent duplicates
        }
        const loadingMessage: Message = { id: loadingId, role: 'assistant', content: 'Thinking...', isLoading: true, timestamp: new Date() };
        const newState: AppState = {
            ...state,
            messagesBySession: {
                ...state.messagesBySession,
                [sessionId]: [...currentMessages, loadingMessage]
            }
        };
        log(`Reducer State After ADD_LOADING_MESSAGE for ${sessionId}: Messages count = ${newState.messagesBySession[sessionId]?.length}`);
        return newState;
    }
    case 'INITIALIZE_SESSION': {
        const { temporarySessionId, finalSessionId } = action.payload;
        if (temporarySessionId === finalSessionId) {
             log(`Reducer INITIALIZE_SESSION: temporary and final IDs are the same (${finalSessionId}), no action needed.`);
             return state;
        }
        let nextMessagesBySession = { ...state.messagesBySession };
        const messagesToMove = nextMessagesBySession[temporarySessionId];

        if (!messagesToMove) {
            log(`Reducer INITIALIZE_SESSION: No messages found for temporary ID ${temporarySessionId}. Cannot initialize ${finalSessionId}.`);
            return state; // Or potentially initialize finalSessionId as empty?
        }

        log(`Reducer INITIALIZE_SESSION: Moving messages from ${temporarySessionId} to ${finalSessionId}.`);
        nextMessagesBySession[finalSessionId] = messagesToMove;
        delete nextMessagesBySession[temporarySessionId];

        const newState: AppState = { ...state, messagesBySession: nextMessagesBySession };
        log(`Reducer State After INITIALIZE_SESSION: Session keys = ${Object.keys(newState.messagesBySession)}`);
        return newState;
    }
    case 'PROCESS_ASSISTANT_RESPONSE': {
        // Simplified: Assumes session is already initialized by INITIALIZE_SESSION if it was new.
        const { sessionId, loadingId, assistantMessage } = action.payload;
        console.log('PROCESS_ASSISTANT_RESPONSE received with payload:', action.payload);
        
        let nextMessagesBySession = { ...state.messagesBySession };
        console.log('Current messagesBySession:', state.messagesBySession);
        
        const currentMessages = nextMessagesBySession[sessionId];
        console.log(`Current messages for session ${sessionId}:`, currentMessages);

        if (!currentMessages) {
            console.error(`ERROR: PROCESS_ASSISTANT_RESPONSE: No messages found for session ${sessionId}. Cannot add assistant message.`);
            log(`ERROR: PROCESS_ASSISTANT_RESPONSE: No messages found for session ${sessionId}. Cannot add assistant message.`);
            return state;
        }

        log(`Reducer PROCESS_ASSISTANT_RESPONSE: Updating session ${sessionId}`);
        console.log(`Reducer PROCESS_ASSISTANT_RESPONSE: Updating session ${sessionId}`);
        
        // Create a completely new array to ensure React detects the state change
        const updatedMessages = [...currentMessages
            .filter(msg => msg.id !== loadingId), // Remove specific loading ID
            assistantMessage]; // Append the new assistant message
        
        console.log('Updated messages after filtering and adding assistant message:', updatedMessages);

        // Create a new object for the session's messages to ensure state immutability
        nextMessagesBySession = {
            ...nextMessagesBySession,
            [sessionId]: updatedMessages
        };
        
        console.log('New messagesBySession:', nextMessagesBySession);
        
        // Create a completely new state object to ensure React triggers a re-render
        const finalState: AppState = { 
            ...state, 
            messagesBySession: nextMessagesBySession 
        };
        
        log(`Reducer State After PROCESS_ASSISTANT_RESPONSE for ${sessionId}: Messages count = ${updatedMessages?.length}`);
        console.log(`Reducer State After PROCESS_ASSISTANT_RESPONSE for ${sessionId}: Messages count = ${updatedMessages?.length}`);
        console.log('Final state:', finalState);
        
        return finalState;
    }
    case 'SET_MESSAGES': {
      const { sessionId, messages } = action.payload;
      
      // Extra debugging for message loading
      log(`SET_MESSAGES for ${sessionId}: Got ${messages?.length} messages`);
      
      // Don't overwrite with empty arrays
      if (!messages || messages.length === 0) {
        log(`SET_MESSAGES: Ignoring empty messages array for ${sessionId}`);
        return state;
      }
      
      log(`First message: ${JSON.stringify(messages[0])}`);
      
      // Check if we already have messages for this session that are more recent
      const existingMessages = state.messagesBySession[sessionId] || [];
      if (existingMessages.length > messages.length) {
        log(`SET_MESSAGES: Existing messages (${existingMessages.length}) are more than new messages (${messages.length}), keeping existing`);
        return state;
      }
      
      // Force properly typed timestamps for all messages
      const processedMessages = messages.map(msg => ({
        ...msg,
        timestamp: msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp || Date.now())
      }));
      
      const newState: AppState = {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: processedMessages
        }
      };
      log(`Reducer State After SET_MESSAGES for ${sessionId}: Messages count = ${newState.messagesBySession[sessionId]?.length}`);
      
      // Trigger a re-render
      setTimeout(() => {
        log(`Forced re-render after SET_MESSAGES for ${sessionId}`);
      }, 0);
      
      return newState;
    }
    case 'REMOVE_MESSAGE': {
        const { sessionId, messageId } = action.payload;
        const currentMessages = state.messagesBySession?.[sessionId] || [];
        const newState: AppState = {
            ...state,
            messagesBySession: {
                ...state.messagesBySession,
                [sessionId]: currentMessages.filter(msg => msg.id !== messageId)
            }
        };
        log(`Reducer State After REMOVE_MESSAGE for ${sessionId}: Removed ${messageId}, Messages count = ${newState.messagesBySession[sessionId]?.length}`);
        return newState;
    }
    
    case 'ADD_SYSTEM_MESSAGE': {
        const { sessionId, message } = action.payload;
        const currentMessages = state.messagesBySession?.[sessionId] || [];
        
        // Check if a message with the same ID already exists (prevent duplicates)
        const existingMessageIndex = currentMessages.findIndex(msg => msg.id === message.id);
        
        // If message already exists with the same ID, update it instead of adding
        if (existingMessageIndex !== -1) {
            log(`Reducer ADD_SYSTEM_MESSAGE: Message with ID ${message.id} already exists, updating instead`);
            
            // Create a new array with the updated message
            const updatedMessages = [...currentMessages];
            updatedMessages[existingMessageIndex] = message;
            
            const newState: AppState = {
                ...state,
                messagesBySession: {
                    ...state.messagesBySession,
                    [sessionId]: updatedMessages
                }
            };
            log(`Reducer State After ADD_SYSTEM_MESSAGE (update) for ${sessionId}: Updated system message, Messages count = ${newState.messagesBySession[sessionId]?.length}`);
            return newState;
        }
        
        // Add as a new message if ID doesn't exist
        const newState: AppState = {
            ...state,
            messagesBySession: {
                ...state.messagesBySession,
                [sessionId]: [...currentMessages, message]
            }
        };
        log(`Reducer State After ADD_SYSTEM_MESSAGE for ${sessionId}: Added system message, Messages count = ${newState.messagesBySession[sessionId]?.length}`);
        return newState;
    }
    // Update an existing system message
    case 'UPDATE_SYSTEM_MESSAGE': {
        const { sessionId, systemMessageId, message } = action.payload;
        const currentMessages = state.messagesBySession?.[sessionId] || [];
        
        // Find the message to update
        const messageIndex = currentMessages.findIndex(msg => msg.id === systemMessageId);
        
        // If message not found, return state unchanged
        if (messageIndex === -1) {
            log(`Reducer UPDATE_SYSTEM_MESSAGE: No message with ID ${systemMessageId} found for session ${sessionId}.`);
            return state;
        }
        
        // Update the message
        const updatedMessages = [...currentMessages];
        updatedMessages[messageIndex] = message;
        
        const newState: AppState = {
            ...state,
            messagesBySession: {
                ...state.messagesBySession,
                [sessionId]: updatedMessages
            }
        };
        
        log(`Reducer State After UPDATE_SYSTEM_MESSAGE for ${sessionId}: Updated system message ${systemMessageId}, Messages count = ${newState.messagesBySession[sessionId]?.length}`);
        return newState;
    }
    
    // Added case for removing loading indicator
    case 'REMOVE_LOADING_INDICATOR': {
        const { sessionId } = action.payload;
        const currentMessages = state.messagesBySession?.[sessionId] || [];
        const updatedMessages = currentMessages.filter(msg => !msg.isLoading); // Remove any message with isLoading flag
        if (currentMessages.length === updatedMessages.length) {
            log(`Reducer REMOVE_LOADING_INDICATOR: No loading indicator found for session ${sessionId}.`);
            return state; // No change needed
        }
        const newState: AppState = {
            ...state,
            messagesBySession: {
                ...state.messagesBySession,
                [sessionId]: updatedMessages
            }
        };
        log(`Reducer State After REMOVE_LOADING_INDICATOR for ${sessionId}: Messages count = ${newState.messagesBySession[sessionId]?.length}`);
        return newState;
    }
    
    case 'PROCESS_ASSISTANT_RESPONSE': {
        const { sessionId, loadingId, assistantMessage } = action.payload;
        const currentMessages = state.messagesBySession?.[sessionId] || [];
        
        // If this is a loading message (isLoading=true), simply add it
        if (assistantMessage.isLoading) {
            const newState: AppState = {
                ...state,
                messagesBySession: {
                    ...state.messagesBySession,
                    [sessionId]: [...currentMessages, assistantMessage]
                }
            };
            log(`Reducer State After PROCESS_ASSISTANT_RESPONSE (loading) for ${sessionId}: Added loading message, Messages count = ${newState.messagesBySession[sessionId]?.length}`);
            return newState;
        }
        
        // If this is a response message, replace the loading message with this one
        // First find if there's a loading message to replace
        const loadingMsgIndex = currentMessages.findIndex(msg => msg.isLoading);
        
        if (loadingMsgIndex >= 0) {
            // Replace the loading message with the actual response
            const updatedMessages = [...currentMessages];
            updatedMessages[loadingMsgIndex] = assistantMessage;
            
            const newState: AppState = {
                ...state,
                messagesBySession: {
                    ...state.messagesBySession,
                    [sessionId]: updatedMessages
                }
            };
            log(`Reducer State After PROCESS_ASSISTANT_RESPONSE (replace) for ${sessionId}: Replaced loading message, Messages count = ${newState.messagesBySession[sessionId]?.length}`);
            return newState;
        } else {
            // No loading message found, just add the new message
            const newState: AppState = {
                ...state,
                messagesBySession: {
                    ...state.messagesBySession,
                    [sessionId]: [...currentMessages, assistantMessage]
                }
            };
            log(`Reducer State After PROCESS_ASSISTANT_RESPONSE (direct) for ${sessionId}: Added assistant message, Messages count = ${newState.messagesBySession[sessionId]?.length}`);
            return newState;
        }
    }
    case 'SET_ACTIVE_MODULE':
      return { ...state, activeModule: action.payload };
    default:
      const exhaustiveCheck: never = action;
      log(`Reducer Action: Unknown type ${(action as any)?.type}`);
      return state;
  }
}

const defaultAppContextValue: AppContextType = {
    state: initialState,
    dispatch: () => null,
};
const AppContext = React.createContext<AppContextType>(defaultAppContextValue);


export function useApp(): AppContextType {
  const context = useContext(AppContext);
  if (context === undefined) throw new Error('useApp must be used within an AppProvider');
  return context;
}

interface AppProviderProps {
    children: React.ReactNode;
}

const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  console.log("--- AppProvider Render ---");
  console.log("--- AppProvider: About to call useReducer ---");
  const [state, dispatch] = useReducer(appReducer, initialState);
  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>;
};


const App: React.FC = () => {
  console.log("--- App Render (Outer) ---");
  
  // Initialize the application on first render
  useEffect(() => {
    console.log("--- App Component: Initializing application ---");
    appInitService.initialize().catch(error => {
      console.error("Failed to initialize application:", error);
    });
  }, []);
  
  console.log("--- App Component: Reached return statement ---");
  return (
    <ThemeProvider theme={theme}>
      <GlobalStyle /> {/* Apply global styles here */}
      <AuthProvider>
        <AppProvider>
          <AppRouter />
        </AppProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};


export default App;
// const AppContentWrapper: React.FC = () => { ... }; // Removed
