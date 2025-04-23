import React, { createContext, useState, useContext, useEffect, ReactNode, useCallback } from 'react';
import raiAPIClient from '../api/rai_api';

// Import Session type
import type { Session } from '../api/rai_api';

interface SessionState {
  sessions: Session[] | null;
  isLoading: boolean;
  error: string | null;
}

interface SessionContextType extends SessionState {
  fetchSessions: () => Promise<Session[] | null>;
  createSession: (title: string) => Promise<Session | null>;
  deleteSession: (sessionId: string) => Promise<boolean>;
  isFetchingSessions: boolean; // Add this property for compatibility with ChatLibrary
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

interface SessionProviderProps {
  children: ReactNode;
}

export const SessionProvider: React.FC<SessionProviderProps> = ({ children }) => {
  const [sessionState, setSessionState] = useState<SessionState>({
    sessions: null,
    isLoading: false,
    error: null
  });

  // Fetch all sessions
  const fetchSessions = useCallback(async (): Promise<Session[] | null> => {
    setSessionState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await raiAPIClient.getChatSessions();
      if (response && response.sessions) {
        setSessionState({
          sessions: response.sessions,
          isLoading: false,
          error: null
        });
        return response.sessions;
      }
      setSessionState((prev) => ({ ...prev, isLoading: false }));
      return null;
    } catch (error) {
      console.error('Error fetching sessions:', error);
      setSessionState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch sessions'
      }));
      return null;
    }
  }, []);

  // Create a new session
  const createSession = useCallback(async (title: string): Promise<Session | null> => {
    try {
      // Since there's no direct createSession method, we'll send a message to create a session
      const response = await raiAPIClient.sendMessage({
        message: `Create new chat: ${title}`,
        sessionId: 'new_chat' // Use a string ID to create a new session
      });
      
      if (response && response.session_id) {
        const newSession: Session = {
          id: response.session_id,
          title: response.title || title,
          timestamp: new Date().toISOString(),
          last_modified: new Date().toISOString() // Add required last_modified field
        };
        
        setSessionState((prev) => ({
          ...prev,
          sessions: prev.sessions ? [...prev.sessions, newSession] : [newSession]
        }));
        
        return newSession;
      }
      return null;
    } catch (error) {
      console.error('Error creating session:', error);
      setSessionState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to create session'
      }));
      return null;
    }
  }, []);

  // Delete a session
  const deleteSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
      const response = await raiAPIClient.deleteChatSession(sessionId);
      // Check if the response is successful based on its status property
      const success = response && typeof response === 'object' && response.status === 'success';
      
      if (success) {
        setSessionState((prev) => ({
          ...prev,
          sessions: prev.sessions ? prev.sessions.filter(s => s.id !== sessionId) : null
        }));
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error deleting session:', error);
      setSessionState((prev) => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to delete session'
      }));
      return false;
    }
  }, []);

  // Initial fetch of sessions
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return (
    <SessionContext.Provider
      value={{
        ...sessionState,
        fetchSessions,
        createSession,
        deleteSession,
        isFetchingSessions: sessionState.isLoading // Map isLoading to isFetchingSessions for compatibility
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};

export const useSession = (): SessionContextType => {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
};
