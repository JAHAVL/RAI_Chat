import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import type { Message } from './chat';
import ChatLibrary from '../../modules/chat_library/ChatLibrary';
import AttachButton from './components/AttachButton';
import ChatMessageComponent from './components/ChatMessageComponent';
import SystemMessageComponent from './components/SystemMessageComponent';

// Import the new ChatContext instead of App context
import { useChat, NEW_CHAT_SESSION_ID } from '../../contexts/ChatContext';

// Import services for chat library
import { sessionService, chatLibraryService } from '../../services/chat';

// Import services
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
  // Use the new ChatContext instead of App context
  const { state, sendMessage } = useChat();
  
  const [input, setInput] = useState<string>('');
  const chatLibraryRef = useRef<any>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get messages from the chat context state
  const currentMessages = state.messagesBySession[currentSessionId] || [];

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
      if (lastMessage) {
        console.log(`STAGE 4 - Last message role: ${lastMessage.role}`);
        console.log(`STAGE 4 - Last message content: ${typeof lastMessage.content === 'string' ? 
          lastMessage.content.substring(0, 100) : 
          JSON.stringify(lastMessage.content).substring(0, 100)}...`);
      }
    }
  }, [currentMessages]);

  // Effect to handle session changes and load messages
  useEffect(() => {
    if (currentSessionId === NEW_CHAT_SESSION_ID) {
        inputRef.current?.focus();
    }
  }, [currentSessionId]);

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return;
    
    try {
      // Clear input field immediately for better UX
      setInput('');
      
      // Call the sendMessage function from the ChatContext
      // Note: The ChatContext sendMessage function already handles:
      // - Adding the user message
      // - Creating a loading message
      // - Sending the message to the backend
      // - Updating the state with the assistant's response
      await sendMessage(message, currentSessionId);
      
      // After successfully sending, check if we need to update the session ID
      // Important: ChatContext will update its internal state.currentSessionId
      if (currentSessionId === NEW_CHAT_SESSION_ID) {
        const newSessionId = state.currentSessionId;
        if (newSessionId && newSessionId !== NEW_CHAT_SESSION_ID) {
          // Update UI state to match the context state
          setCurrentSessionId(newSessionId);
          
          // Handle chat library update
          onConfirmNewChat(`temp-${Date.now()}`, {
            id: newSessionId,
            title: typeof message === 'string' ? message.substring(0, 30) : JSON.stringify(message).substring(0, 30)
          });
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      alert(`Error sending message: ${error instanceof Error ? error.message : 'Unknown error'}`);
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