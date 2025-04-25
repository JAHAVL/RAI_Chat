import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { useApp } from '../../App';
import type { Message } from './chat';
import ChatLibrary from '../../modules/chat_library/ChatLibrary';
import AttachButton from './components/AttachButton';
import ChatMessageComponent from './components/ChatMessageComponent';
import SystemMessageComponent from './components/SystemMessageComponent';

// Import services
import { messageService, sessionService, chatLibraryService, NEW_CHAT_SESSION_ID } from '../../services/chat';
import backendApiInterface from '../../api/backend_api_interface';

// --- Type Definitions ---
type SessionId = string;

interface AppContentProps {
  currentSessionId: SessionId;
  setCurrentSessionId: React.Dispatch<React.SetStateAction<SessionId>>;
  onNewChatPlaceholder: (tempId: string, initialTitle: string) => void;
  onConfirmNewChat: (tempId: string, realSessionData: { id: string; title: string }) => void;
  onFailedNewChat: (tempId: string) => void;
  isChatLibraryOpen?: boolean;
  setIsChatLibraryOpen?: React.Dispatch<React.SetStateAction<boolean>>;
}

// --- Styled Components ---
const MessagesArea = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${props => props.theme.spacing.md};
  padding-top: 60px; /* Adjust if header height changes */
  padding-bottom: 40px; /* Adjust if footer height changes */
  background-color: #0A0A0A; /* Solid very dark background */
`;

const Footer = styled.div`
  position: relative; z-index: 150; display: flex; align-items: flex-end;
`;

const InputWrapperWithBorder = styled.div`
  display: flex; align-items: flex-end; width: 100%; background-color: #121212;
  padding: ${props => props.theme.spacing.md}; border-top: 1px solid rgba(255, 255, 255, 0.1); box-sizing: border-box;
`;

const InputField = styled.textarea`
  flex: 1;
  min-height: 24px; /* Smaller initial height */
  max-height: 150px;
  background-color: rgba(255, 255, 255, 0.05);
  border: none;
  border-radius: 22px;
  padding: 12px 16px;
  color: ${props => props.theme.colors.text};
  font-size: ${props => props.theme.typography.fontSize.md};
  resize: none;
  outline: none;
  
  &::placeholder {
    color: rgba(255, 255, 255, 0.4);
  }
`;

const IconButton = styled.button<{ disabled?: boolean }>`
  background: none;
  border: none;
  color: ${props => props.disabled ? 'rgba(255, 255, 255, 0.3)' : props.theme.colors.accent};
  cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
  padding: 8px;
  margin-left: 4px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
  
  &:hover {
    background-color: ${props => props.disabled ? 'transparent' : 'rgba(59, 130, 246, 0.1)'};
  }
`;

// --- App Content Component (Now ChatPage) ---
const ChatPage: React.FC<AppContentProps> = ({
  currentSessionId,
  setCurrentSessionId,
  onNewChatPlaceholder,
  onConfirmNewChat,
  onFailedNewChat,
  isChatLibraryOpen,
  setIsChatLibraryOpen
}) => {
  const { state, dispatch } = useApp();
  const [input, setInput] = useState<string>('');
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const chatLibraryRef = useRef<any>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get messages from global state
  const stateMessages: Message[] = (state?.messagesBySession?.[currentSessionId])
                         ? state.messagesBySession[currentSessionId]!
                         : [];
                         
  // Combine local and state messages, prioritizing local ones
  // This gives us a direct path for messages while still respecting the global state
  const currentMessages = localMessages.length > 0 ? localMessages : stateMessages;

  // Set initial height on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = '24px'; // Force small initial height
    }
  }, []);

  // Adjust height as content changes
  useEffect(() => {
    if (inputRef.current) {
      const minHeight = 24;
      const maxHeight = 150;

      // Reset to auto to get the correct scrollHeight
      inputRef.current.style.height = 'auto';

      // Calculate the new height based on content
      const scrollHeight = inputRef.current.scrollHeight;
      const newHeight = Math.max(minHeight, Math.min(scrollHeight, maxHeight));

      // Set the new height
      inputRef.current.style.height = `${newHeight}px`;
    }
  }, [input]);

  useEffect(() => {
    // Scroll to bottom whenever messages change
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
    
    // STAGE 4: Log what messages are being rendered in the UI
    console.log(`STAGE 4 - ChatPage rendering messages for session: ${currentSessionId}`);
    console.log(`STAGE 4 - Message count: ${currentMessages.length}`);
    if (currentMessages.length > 0) {
      // Log the last message which should be the assistant's response
      const lastMessage = currentMessages[currentMessages.length - 1];
      console.log(`STAGE 4 - Last message role: ${lastMessage.role}`);
      console.log(`STAGE 4 - Last message content: ${lastMessage.content.substring(0, 100)}...`);
    }
    
    // Load session messages if needed (e.g., on first load)
    sessionService.loadSessionMessages(currentSessionId, currentMessages, dispatch);
  }, [currentMessages]);

  // Effect to handle session changes and load messages
  useEffect(() => {
    if (currentSessionId === NEW_CHAT_SESSION_ID) {
        inputRef.current?.focus();
    }
    
    // Use the sessionService to load messages
    const currentMessages = state?.messagesBySession?.[currentSessionId];
    sessionService.loadSessionMessages(currentSessionId, currentMessages, dispatch);
    
  }, [currentSessionId, dispatch, state.messagesBySession]);

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return;
    
    try {
      // Clear input field immediately for better UX
      setInput('');
      
      // Create a user message to show immediately
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date()
      };
      
      // Create a loading message to show while waiting for response
      const loadingMessage: Message = {
        id: `loading-${Date.now()}`,
        role: 'assistant',
        content: 'Thinking...',
        timestamp: new Date(),
        isLoading: true
      };
      
      // Update local messages immediately to show user message and loading indicator
      setLocalMessages(prev => [...prev, userMessage, loadingMessage]);
      
      // Make the API request directly
      const backendApi = backendApiInterface;
      const response = await backendApi.sendMessage(currentSessionId, message);
      
      console.log('Direct API response:', response);
      
      // Extract content directly from the response
      let responseContent = '';
      if (response.content) {
        responseContent = response.content;
        console.log('Found content field:', responseContent);
      } else if (response.tier3) {
        responseContent = response.tier3;
        console.log('Found tier3 field:', responseContent);
      } else {
        responseContent = 'No response received (direct path)';
        console.error('No content found in response:', response);
      }
      
      // Create the assistant message
      const assistantMessage: Message = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: responseContent,
        timestamp: new Date()
      };
      
      // If we're in a new chat, handle session ID update
      if (currentSessionId === NEW_CHAT_SESSION_ID && response.sessionId) {
        // Update session ID
        setCurrentSessionId(response.sessionId);
        
        // Handle chat placeholder
        const title = response.title || message.substring(0, 30);
        onConfirmNewChat(`temp-${Date.now()}`, {
          id: response.sessionId,
          title
        });
      }
      
      // Update local messages, replacing loading indicator with real response
      setLocalMessages(prev => {
        // Find and remove the loading message
        const withoutLoading = prev.filter(msg => !msg.isLoading);
        
        // Add the assistant message
        return [...withoutLoading, assistantMessage];
      });
      
      // Still dispatch to global state as a backup - use supported action types
      // First add the user message
      dispatch({ 
        type: 'ADD_USER_MESSAGE', 
        payload: { 
          sessionId: response.sessionId || currentSessionId, 
          message: userMessage
        } 
      });
      
      // Then add the assistant response
      dispatch({
        type: 'PROCESS_ASSISTANT_RESPONSE',
        payload: {
          sessionId: response.sessionId || currentSessionId,
          loadingId: loadingMessage.id,
          assistantMessage: assistantMessage
        }
      });
      
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Create error message
      const errorMessage: Message = {
        id: Math.random().toString(36).substr(2, 9),
        role: 'system',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
        messageType: 'error'
      };
      
      // Update local messages with error
      setLocalMessages(prev => {
        // Remove any loading message
        const withoutLoading = prev.filter(msg => !msg.isLoading);
        return [...withoutLoading, errorMessage];
      });
      
      // Also update global state
      dispatch({ 
        type: 'ADD_SYSTEM_MESSAGE', 
        payload: { 
          sessionId: currentSessionId, 
          message: errorMessage 
        } 
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(input);
    }
  };

  const handleToggleChatLibrary = () => {
    if (setIsChatLibraryOpen) {
      setIsChatLibraryOpen(prev => !prev);
    }
  };

  const handleNewChatPlaceholder = (tempId: string, initialTitle: string) => {
    chatLibraryService.addPlaceholder(chatLibraryRef, tempId, initialTitle);
  };

  const handleConfirmNewChat = (tempId: string, realSessionData: { id: string; title: string }) => {
    chatLibraryService.confirmPlaceholder(chatLibraryRef, tempId, realSessionData);
  };

  const handleFailedNewChat = (tempId: string) => {
    chatLibraryService.removePlaceholder(chatLibraryRef, tempId);
  };

  const handleAttachClick = () => {
    console.log("Attach button clicked!");
  };

  return (
    <>
      <ChatLibrary
        ref={chatLibraryRef}
        isOpen={isChatLibraryOpen ?? true}
        onSelectChat={(sessionId) => setCurrentSessionId(sessionId)}
        onNewChat={() => setCurrentSessionId(NEW_CHAT_SESSION_ID)}
        currentSessionId={currentSessionId}
        onChatDeleted={(deletedSessionId) => {
          if (currentSessionId === deletedSessionId) {
            setCurrentSessionId(NEW_CHAT_SESSION_ID);
          }
        }}
      />
      <MessagesArea>
        {currentMessages.map((msg) => {
          if (msg.role === 'system') {
            return <SystemMessageComponent key={msg.id} message={msg} />;
          }
          return <ChatMessageComponent key={msg.id} message={msg} />;
        })}
        <div ref={messagesEndRef} />
      </MessagesArea>
      <Footer>
        <InputWrapperWithBorder>
          <InputField
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            rows={1}
          />
          <AttachButton onClick={handleAttachClick} />
          <IconButton onClick={() => handleSendMessage(input)} disabled={!input.trim()}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </IconButton>
        </InputWrapperWithBorder>
      </Footer>
    </>
  );
};

export default ChatPage;