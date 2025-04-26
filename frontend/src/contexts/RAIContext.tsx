import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
// Import the client and necessary types from backend_api_interface.ts
import backendApi, { 
  Message,
  ApiResponse,
  ChatMessageResponse
} from '../api/backend_api_interface';
// Import Message type from correct location if needed for additional properties
import type { Message as UIMessage } from '../pages/Main_Chat_UI/chat.d';

// --- Type Definitions ---

// Define the shape of the context value
interface RAIContextType {
  isConnected: boolean;
  isLoading: boolean;
  messages: UIMessage[]; // Use the Message type
  memory: any | null; // Type more specifically if memory structure is known
  llmInfo: any | null; // Type more specifically if llmInfo structure is known
  error: string | null;
  sendMessage: (message: string) => Promise<ChatMessageResponse | { error: string }>; // Adjust return type based on implementation
  generateText: (prompt: string, options?: object) => Promise<any | { error: string }>; // Adjust return type
  resetConversation: () => Promise<ApiResponse | { error: string }>; // Adjust return type
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
  const [messages, setMessages] = useState<UIMessage[]>([]); // Use Message type
  const [memory, setMemory] = useState<any | null>(null); // Use specific type if known
  const [llmInfo, setLLMInfo] = useState<any | null>(null); // Use specific type if known
  const [error, setError] = useState<string | null>(null);

  // Initialize connection to RAI API
  useEffect(() => {
    let isMounted = true; // Flag to prevent state updates on unmounted component
    const initConnection = async () => {
      try {
        // Check API health
        const health = await backendApi.healthCheck();
        // Use 'success' based on RaiApiResponse
        if (isMounted && health.status === 'success') {
          setIsConnected(true);
          setError(null); // Clear error on success

          // Get LLM info
          try {
              const llmInfoResponse = await backendApi.getLLMInfo();
              if (isMounted && llmInfoResponse.status === 'success') {
                // Assuming the actual info is in a property like 'model_info' based on original code
                setLLMInfo(llmInfoResponse.model_info || llmInfoResponse);
              }
          } catch (llmErr: any) {
              console.warn('Failed to get LLM info:', llmErr.message);
              // Don't necessarily set a global error for this optional info
          }

          // Add initial system message
          const initialMessage: UIMessage = {
              id: 'sys-initial', // Add an ID for key prop
              role: 'system',
              content: "Hi, I'm R.ai. How can I help?",
              timestamp: new Date() // Add timestamp
          };
          if (isMounted) setMessages([initialMessage]);

          // Get memory
          try {
              const memoryResponse = await backendApi.getMemory();
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
        const health = await backendApi.healthCheck();
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
  const sendMessage = async (message: string): Promise<ChatMessageResponse | { error: string }> => {
    try {
      setIsLoading(true);
      setError(null);

      // Add user message to chat state
      const userMessage: UIMessage = {
        id: `user-${Date.now()}`, // Add unique id
        role: 'user',
        content: message,
        timestamp: new Date() // Add timestamp
      };
      setMessages(prevMessages => [...prevMessages, userMessage]);

      // Get active session ID (would need to be passed in or stored in state)
      const sessionId = 'current'; // Placeholder, replace with actual session ID
      
      // Send message to backend
      const response = await backendApi.sendMessage(sessionId, message);
      
      setIsLoading(false);

      if (response && !response.error) {
        // Build assistant message from response
        const assistantMessage: UIMessage = {
          id: response.id || `resp-${Date.now()}`, // Use response ID or generate
          role: 'assistant',
          content: response.content || response.response || 'I received your message',
          timestamp: new Date() // Use current time as timestamp
        };
        
        // Add assistant message to messages state
        setMessages(prevMessages => [...prevMessages, assistantMessage]);
        
        return response;
      } else {
        const errorMsg = response.error || 'Failed to get response from server';
        setError(errorMsg);
        
        // Add error message as assistant message
        const errorResponse: UIMessage = {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Sorry, there was an error: ${errorMsg}`,
          timestamp: new Date()
        };
        setMessages(prevMessages => [...prevMessages, errorResponse]);
        
        return { error: errorMsg };
      }
    } catch (err: any) {
      console.error('Error sending message:', err);
      const errorMessage = err.message || 'Failed to connect to the server';

      // Add error message to chat state
      const errorResponse: UIMessage = {
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
  const generateText = async (prompt: string, options: object = {}): Promise<any | { error: string }> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await backendApi.generateText(prompt, options);

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
  const resetConversation = async (): Promise<ApiResponse | { error: string }> => {
    try {
      setIsLoading(true);
      setError(null);

      // Reset session on API (using placeholder)
      const response = await backendApi.resetSession();

      if (response.status === 'success') {
        // Reset local state
        const initialMessage: UIMessage = {
            id: 'sys-reset', role: 'system', content: "Conversation reset. How can I help?", timestamp: new Date()
        };
        setMessages([initialMessage]);

        // Reset memory (using placeholder)
        try {
            const memoryResponse = await backendApi.getMemory();
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
