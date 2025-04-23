import React, { createContext, useContext, useState, useReducer, useCallback } from 'react';
import type { Message } from '../pages/Main_Chat_UI/chat.d'; // Import Message type from chat.d.ts
import systemMessageService, { SystemMessageType } from '../services/chat/systemMessageService';

type Module = 'chat' | 'video' | 'code-editor';

interface AppState {
  messagesBySession: Record<string, Message[]>;
  systemMessagesBySession: Record<string, Message[]>;
  activeModule: Module;
  loading: boolean;
  currentSessionId: string | null;
}

type AppAction =
  | { type: 'SET_ACTIVE_MODULE'; payload: Module }
  | { type: 'ADD_USER_MESSAGE'; payload: { sessionId: string; message: Message } }
  | { type: 'ADD_ASSISTANT_MESSAGE'; payload: { sessionId: string; message: Message } }
  | { type: 'ADD_SYSTEM_MESSAGE'; payload: { sessionId: string; message: Message } }
  | { type: 'SET_SYSTEM_MESSAGES'; payload: { sessionId: string; messages: Message[] } }
  | { type: 'INITIALIZE_SESSION'; payload: { temporarySessionId: string; finalSessionId: string } }
  | { type: 'CLEAR_SESSION'; payload: { sessionId: string } }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_CURRENT_SESSION_ID'; payload: string }
  | { type: 'CLEAR_MESSAGES'; payload: { sessionId: string } };

// Create initial welcome message
const initialWelcomeMessage: Message = {
  id: `sys-welcome-${Date.now()}`,
  role: 'system',
  content: "Hey, I'm R.ai. How can I help you today?",
  timestamp: new Date(),
  messageType: SystemMessageType.WELCOME
};

const initialState: AppState = {
  messagesBySession: {
    'new_chat': []
  },
  systemMessagesBySession: {
    'new_chat': [initialWelcomeMessage]
  },
  activeModule: 'chat',
  loading: false,
  currentSessionId: 'new_chat',
};

const reducer = (state: AppState, action: AppAction): AppState => {
  switch (action.type) {
    case 'SET_ACTIVE_MODULE':
      return { ...state, activeModule: action.payload };
      
    case 'ADD_USER_MESSAGE': {
      const { sessionId, message } = action.payload;
      const sessionMessages = state.messagesBySession[sessionId] || [];
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: [...sessionMessages, message]
        }
      };
    }
    
    case 'ADD_ASSISTANT_MESSAGE': {
      const { sessionId, message } = action.payload;
      const sessionMessages = state.messagesBySession[sessionId] || [];
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: [...sessionMessages, message]
        }
      };
    }
    
    case 'ADD_SYSTEM_MESSAGE': {
      const { sessionId, message } = action.payload;
      const sessionSystemMessages = state.systemMessagesBySession[sessionId] || [];
      return {
        ...state,
        systemMessagesBySession: {
          ...state.systemMessagesBySession,
          [sessionId]: [...sessionSystemMessages, message]
        }
      };
    }
    
    case 'SET_SYSTEM_MESSAGES': {
      const { sessionId, messages } = action.payload;
      return {
        ...state,
        systemMessagesBySession: {
          ...state.systemMessagesBySession,
          [sessionId]: messages
        }
      };
    }
    
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
      
    case 'SET_CURRENT_SESSION_ID':
      return { ...state, currentSessionId: action.payload };
      
    case 'INITIALIZE_SESSION': {
      const { temporarySessionId, finalSessionId } = action.payload;
      
      // Get messages from temporary session
      const tempMessages = state.messagesBySession[temporarySessionId] || [];
      const tempSystemMessages = state.systemMessagesBySession[temporarySessionId] || [];
      
      // Create new state with messages moved to final session ID
      const newMessages = { ...state.messagesBySession };
      const newSystemMessages = { ...state.systemMessagesBySession };
      
      // Delete temporary session and create final session
      delete newMessages[temporarySessionId];
      delete newSystemMessages[temporarySessionId];
      
      newMessages[finalSessionId] = tempMessages;
      newSystemMessages[finalSessionId] = tempSystemMessages;
      
      return {
        ...state,
        messagesBySession: newMessages,
        systemMessagesBySession: newSystemMessages,
        currentSessionId: finalSessionId
      };
    }
    
    case 'CLEAR_MESSAGES': {
      const { sessionId } = action.payload;
      
      // Create new welcome message for cleared session
      const newWelcomeMessage = systemMessageService.createWelcomeMessage(
        "Conversation cleared. How can I help you today?"
      );
      
      return {
        ...state,
        messagesBySession: {
          ...state.messagesBySession,
          [sessionId]: []
        },
        systemMessagesBySession: {
          ...state.systemMessagesBySession,
          [sessionId]: [newWelcomeMessage]
        }
      };
    }
    
    default:
      return state;
  }
};

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  toggleModule: (module: Module) => void;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  getMessagesForCurrentSession: () => Message[];
  getSystemMessagesForCurrentSession: () => Message[];
}

const AppContext = createContext<AppContextType | undefined>(undefined);

// Helper to dispatch a custom event when AI responds
const dispatchAIResponseEvent = () => {
  const event = new CustomEvent('ai-response');
  document.dispatchEvent(event);
};

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Initialize system messages for a new session
  useCallback((sessionId: string) => {
    // Check if session already has system messages
    if (!state.systemMessagesBySession[sessionId]) {
      // Fetch system messages from backend
      systemMessageService.fetchSystemMessages(sessionId, dispatch);
    }
  }, [state.systemMessagesBySession]);

  const toggleModule = useCallback((module: Module) => {
    dispatch({ type: 'SET_ACTIVE_MODULE', payload: module });
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    };

    // Add user message
    dispatch({ 
      type: 'ADD_USER_MESSAGE', 
      payload: { 
        sessionId: state.currentSessionId || 'new_chat', 
        message: userMessage 
      } 
    });

    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      // API call would go here
      // For now, simulate a response
      setTimeout(() => {
        const aiMessage: Message = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: `I received your message: "${content}"`,
          timestamp: new Date(),
        };

        dispatch({ 
          type: 'ADD_ASSISTANT_MESSAGE', 
          payload: { 
            sessionId: state.currentSessionId || 'new_chat', 
            message: aiMessage 
          } 
        });
        
        dispatch({ type: 'SET_LOADING', payload: false });
        dispatchAIResponseEvent();
      }, 1000);
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error system message
      const errorMessage = systemMessageService.createErrorMessage(
        'Failed to send message. Please try again.'
      );
      
      dispatch({ 
        type: 'ADD_SYSTEM_MESSAGE', 
        payload: { 
          sessionId: state.currentSessionId || 'new_chat', 
          message: errorMessage 
        } 
      });
      
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [state.currentSessionId]);

  const clearMessages = useCallback(() => {
    if (state.currentSessionId) {
      dispatch({ 
        type: 'CLEAR_MESSAGES', 
        payload: { sessionId: state.currentSessionId } 
      });
    }
  }, [state.currentSessionId]);
  
  const getMessagesForCurrentSession = useCallback(() => {
    if (!state.currentSessionId) return [];
    return state.messagesBySession[state.currentSessionId] || [];
  }, [state.currentSessionId, state.messagesBySession]);
  
  const getSystemMessagesForCurrentSession = useCallback(() => {
    if (!state.currentSessionId) return [];
    return state.systemMessagesBySession[state.currentSessionId] || [];
  }, [state.currentSessionId, state.systemMessagesBySession]);

  return (
    <AppContext.Provider
      value={{
        state,
        dispatch,
        toggleModule,
        sendMessage,
        clearMessages,
        getMessagesForCurrentSession,
        getSystemMessagesForCurrentSession
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

// Custom hook to use the app context
export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export default useApp;
