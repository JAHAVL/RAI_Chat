import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
// Import the client and necessary types from rai_api.ts
import raiAPIClient from '../api/rai_api';
import type {
    HealthStatus,
    LLMInfoResponse,
    MemoryResponse,
    SendMessageResponse,
    GenerateTextResponse,
    ResetSessionResponse
} from '../api/rai_api'; // Adjust path/export if needed
import type { Message } from '../pages/Main_Chat_UI/chat.d'; // Import Message type from correct location

// --- Type Definitions ---

// Define the shape of the context value
interface RAIContextType {
  isConnected: boolean;
  isLoading: boolean;
  messages: Message[]; // Use the Message type
  memory: any | null; // Type more specifically if memory structure is known
  llmInfo: any | null; // Type more specifically if llmInfo structure is known
  error: string | null;
  sendMessage: (message: string) => Promise<SendMessageResponse | { error: string }>; // Adjust return type based on implementation
  generateText: (prompt: string, options?: object) => Promise<GenerateTextResponse | { error: string }>; // Adjust return type
  resetConversation: () => Promise<ResetSessionResponse | { error: string }>; // Adjust return type
}

interface RAIProviderProps {
  children: ReactNode;
}

// Create RAI context with a default undefined value
const RAIContext = createContext<RAIContextType | undefined>(undefined);

/**
 * RAI Provider component
 * Provides RAI Chat functionality to the application
 */
export const RAIProvider: React.FC<RAIProviderProps> = ({ children }) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([]); // Use Message type
  const [memory, setMemory] = useState<any | null>(null); // Use specific type if known
  const [llmInfo, setLLMInfo] = useState<any | null>(null); // Use specific type if known
  const [error, setError] = useState<string | null>(null);

  // Initialize connection to RAI API
  useEffect(() => {
    let isMounted = true; // Flag to prevent state updates on unmounted component
    const initConnection = async () => {
      try {
        // Check API health
        const health: HealthStatus = await raiAPIClient.healthCheck();
        // Use 'success' based on RaiApiResponse
        if (isMounted && health.status === 'success') {
          setIsConnected(true);
          setError(null); // Clear error on success

          // Get LLM info
          try {
              const llmInfoResponse: LLMInfoResponse = await raiAPIClient.getLLMInfo();
              if (isMounted && llmInfoResponse.status === 'success') {
                // Assuming the actual info is in a property like 'model_info' based on original code
                setLLMInfo(llmInfoResponse.model_info || llmInfoResponse);
              }
          } catch (llmErr: any) {
              console.warn('Failed to get LLM info:', llmErr.message);
              // Don't necessarily set a global error for this optional info
          }

          // Add initial system message
          const initialMessage: Message = {
              id: 'sys-initial', // Add an ID for key prop
              role: 'system',
              content: "Hi, I'm R.ai. How can I help?",
              timestamp: new Date() // Add timestamp
          };
          if (isMounted) setMessages([initialMessage]);

          // Get memory
          try {
              const memoryResponse: MemoryResponse = await raiAPIClient.getMemory();
              if (isMounted && memoryResponse.status === 'success') {
                setMemory(memoryResponse.memory);
              }
          } catch (memErr: any) {
               console.warn('Failed to get initial memory:', memErr.message);
               // Don't necessarily set a global error for this optional info
          }

        } else if (isMounted) {
          setIsConnected(false);
          setError(health.error || 'RAI API server is not available');
        }
      } catch (err: any) {
        console.error('Failed to connect to RAI API:', err);
        if (isMounted) {
          setIsConnected(false);
          setError(err.message || 'Failed to connect to RAI API');
        }
      }
    };

    initConnection();

    // Ping API every 30 seconds to check connection status
    const pingInterval = setInterval(async () => {
      try {
        const health = await raiAPIClient.healthCheck();
        if (isMounted) {
            // Use 'success'
            const currentlyConnected = health.status === 'success';
            if (currentlyConnected !== isConnected) {
                 setIsConnected(currentlyConnected);
                 if (!currentlyConnected) {
                     setError('RAI API connection lost.');
                 } else {
                     setError(null);
                 }
            }
        }
      } catch (err) {
        if (isMounted && isConnected) {
            setIsConnected(false);
            setError('RAI API connection failed.');
        }
      }
    }, 30000);

    // Cleanup function
    return () => {
        isMounted = false;
        clearInterval(pingInterval);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Runs once on mount

  /**
   * Send message to RAI
   * @param {string} message Message to send
   * @returns {Promise<SendMessageResponse | { error: string }>} Response object or error object
   */
  const sendMessage = async (message: string): Promise<SendMessageResponse | { error: string }> => {
    try {
      setIsLoading(true);
      setError(null);

      // Add user message to state
      const userMessage: Message = {
          id: `user-${Date.now()}`, // Add ID
          role: 'user',
          content: message,
          timestamp: new Date() // Add timestamp
      };
      setMessages(prevMessages => [...prevMessages, userMessage]);

      // Send message to API (Note: This might be handled by IPC in App.tsx now)
      // If using IPC, this context method might become obsolete or need refactoring
      const response = await raiAPIClient.sendMessage({
        message,
        sessionId: 'new_chat' // Use a string ID to create a new session
      });

      if (response.status === 'success') {
        // Add assistant response to state
        const assistantMessage: Message = {
            id: `asst-${Date.now()}`, // Add ID
            role: 'assistant',
            content: response.response || '...', // Use response content
            timestamp: new Date() // Add timestamp
        };
        setMessages(prevMessages => [...prevMessages, assistantMessage]);

        // Refresh memory (optional, depending on API design)
        try {
            const memoryResponse = await raiAPIClient.getMemory();
            if (memoryResponse.status === 'success') {
              setMemory(memoryResponse.memory);
            }
        } catch (memErr: any) {
            console.warn("Failed to refresh memory after message:", memErr.message);
        }

        setIsLoading(false);
        return response;
      } else {
        const errorMsg = response.error || 'Failed to get response';
        setError(errorMsg);
        setIsLoading(false);
        // Add error message to chat? Maybe not, let component decide based on error object
        return { error: errorMsg };
      }
    } catch (err: any) {
      console.error('Error sending message:', err);
      const errorMessage = err.message || 'Failed to connect to the server';

      // Add error message to chat state
      const errorResponse: Message = {
        id: `err-${Date.now()}`, // Add ID
        role: 'assistant', // Display as assistant message
        content: `Sorry, I encountered an error: ${errorMessage}`,
        timestamp: new Date(), // Add timestamp
        // isError: true // Consider adding a flag if specific styling is needed
      };
      setMessages(prevMessages => [...prevMessages, errorResponse]);

      setError(errorMessage);
      setIsLoading(false);
      return { error: errorMessage };
    }
  };

  /**
   * Generate text with LLM (via RAI backend - Placeholder)
   * @param {string} prompt Prompt for generation
   * @param {object} options Options for generation
   * @returns {Promise<GenerateTextResponse | { error: string }>} Response with generated text or error
   */
  const generateText = async (prompt: string, options: object = {}): Promise<GenerateTextResponse | { error: string }> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await raiAPIClient.generateText(prompt, options); // Using placeholder

      setIsLoading(false);
      if (response.status === 'success') {
          return response;
      } else {
          const errorMsg = response.error || 'Failed to generate text';
          setError(errorMsg);
          return { error: errorMsg };
      }
    } catch (err: any) {
      console.error('Error generating text:', err);
      const errorMsg = err.message || 'Error generating text';
      setError(errorMsg);
      setIsLoading(false);
      return { error: errorMsg };
    }
  };

  /**
   * Reset the conversation (Placeholder)
   * @returns {Promise<ResetSessionResponse | { error: string }>} Reset status or error
   */
  const resetConversation = async (): Promise<ResetSessionResponse | { error: string }> => {
    try {
      setIsLoading(true);
      setError(null);

      // Reset session on API (using placeholder)
      const response = await raiAPIClient.resetSession();

      if (response.status === 'success') {
        // Reset local state
        const initialMessage: Message = {
            id: 'sys-reset', role: 'system', content: "Conversation reset. How can I help?", timestamp: new Date()
        };
        setMessages([initialMessage]);

        // Reset memory (using placeholder)
        try {
            const memoryResponse = await raiAPIClient.getMemory();
            if (memoryResponse.status === 'success') {
              setMemory(memoryResponse.memory);
            } else {
              setMemory(null); // Clear memory if fetch fails
            }
        } catch {
            setMemory(null); // Clear memory on error
        }

        setIsLoading(false);
        return response;
      } else {
          const errorMsg = response.error || 'Failed to reset session';
          setError(errorMsg);
          setIsLoading(false);
          return { error: errorMsg };
      }
    } catch (err: any) {
      console.error('Error resetting conversation:', err);
      const errorMsg = err.message || 'Error resetting conversation';
      setError(errorMsg);
      setIsLoading(false);
      return { error: errorMsg };
    }
  };

  // Context value conforming to RAIContextType
  const contextValue: RAIContextType = {
    isConnected,
    isLoading,
    messages,
    memory,
    llmInfo,
    error,
    sendMessage,
    generateText,
    resetConversation,
  };

  return (
    <RAIContext.Provider value={contextValue}>
      {children}
    </RAIContext.Provider>
  );
};

/**
 * Hook to use RAI functionality
 * @returns {RAIContextType} RAI context
 */
export const useRAI = (): RAIContextType => {
  const context = useContext(RAIContext);
  if (context === undefined) {
    throw new Error('useRAI must be used within a RAIProvider');
  }
  return context;
};

export default RAIContext;
