import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import llmAPIClient from '../api/llm_api';
import type {
    Message,
    ChatCompletionOptions,
    GenerateTextOptions,
    ChatCompletionResponse,
    GenerateTextResponse,
    SessionInfo,
    HealthStatus
} from '../api/llm_api';


interface LLMContextType {
  isConnected: boolean;
  isLoading: boolean;
  session: SessionInfo | null;
  models: string[];
  activeModel: string | null;
  error: string | null;
  sendMessage: (messages: Message[], options?: ChatCompletionOptions) => Promise<ChatCompletionResponse>;
  generateText: (prompt: string, options?: GenerateTextOptions) => Promise<GenerateTextResponse>;
  resetSession: () => Promise<void>;
}

interface LLMProviderProps {
  children: ReactNode;
}

const LLMContext = createContext<LLMContextType | undefined>(undefined);

export const LLMProvider: React.FC<LLMProviderProps> = ({ children }) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const initConnection = async () => {
      try {
        // Check API health
        const health: HealthStatus = await llmAPIClient.healthCheck();
        if (isMounted && health.status === 'success') { // Check status from response ('success' based on ApiResponse)
          setIsConnected(true);
          setError(null); // Clear error on successful connection

          // Get or create session
          const sessionId = await llmAPIClient.getOrCreateSession();
          if (isMounted && sessionId) {
            const sessionInfo = await llmAPIClient.getSessionInfo();
            if (isMounted) {
                setSession(sessionInfo);
                if (sessionInfo?.session?.model) {
                  setActiveModel(sessionInfo.session.model);
                }
            }
          } else if (isMounted) {
              setError('Failed to establish LLM session.');
          }

          // Get available models
          const availableModels = await llmAPIClient.getModels();
          if (isMounted) {
            setModels(availableModels);
            if (!activeModel && availableModels.length > 0) {
            }
          }
        } else if (isMounted) {
          setIsConnected(false);
          setError(health.error || 'LLM API server is not available');
        }
      } catch (err: any) {
        console.error('Failed to connect to LLM API:', err);
        if (isMounted) {
          setIsConnected(false);
          setError(err.message || 'Failed to connect to LLM API');
        }
      }
    };

    initConnection();

    const pingInterval = setInterval(async () => {
      try {
        const health = await llmAPIClient.healthCheck();
        if (isMounted) {
            const currentlyConnected = health.status === 'success';
            if (currentlyConnected !== isConnected) {
                 setIsConnected(currentlyConnected);
                 if (!currentlyConnected) {
                     setError('LLM API connection lost.');
                 } else {
                     setError(null); // Clear error on reconnect
                 }
            }
        }
      } catch (err) {
        if (isMounted && isConnected) {
            setIsConnected(false);
            setError('LLM API connection failed.');
        }
      }
    }, 30000);

    return () => {
      isMounted = false;
      clearInterval(pingInterval);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendMessage = async (messages: Message[], options: ChatCompletionOptions = {}): Promise<ChatCompletionResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await llmAPIClient.chatCompletion(messages, options);
      setIsLoading(false);
      return response;
    } catch (err: any) {
      setError(err.message || 'Failed to get response from LLM');
      setIsLoading(false);
      throw err;
    }
  };

  const generateText = async (prompt: string, options: GenerateTextOptions = {}): Promise<GenerateTextResponse> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await llmAPIClient.generateText(prompt, options);
      setIsLoading(false);
      return response;
    } catch (err: any) {
      setError(err.message || 'Failed to generate text');
      setIsLoading(false);
      throw err; // Re-throw error
    }
  };

  /**
   * Reset current session
   */
  const resetSession = async (): Promise<void> => {
    setIsLoading(true); // Indicate loading during reset
    setError(null);
    try {
      await llmAPIClient.deleteSession();
      const newSessionId = await llmAPIClient.getOrCreateSession();
      if (newSessionId) {
        const sessionInfo = await llmAPIClient.getSessionInfo();
        setSession(sessionInfo);
         if (sessionInfo?.session?.model) {
            setActiveModel(sessionInfo.session.model);
         }
      } else {
          setSession(null);
          setError('Failed to create a new session after reset.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to reset session');
      setSession(null);
    } finally {
        setIsLoading(false);
    }
  };

  const contextValue: LLMContextType = {
    isConnected,
    isLoading,
    session,
    models,
    activeModel,
    error,
    sendMessage,
    generateText,
    resetSession,
  };

  return (
    <LLMContext.Provider value={contextValue}>
      {children}
    </LLMContext.Provider>
  );
};

export const useLLM = (): LLMContextType => {
  const context = useContext(LLMContext);
  if (context === undefined) {
    throw new Error('useLLM must be used within an LLMProvider');
  }
  return context;
};

export default LLMContext;
