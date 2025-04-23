import React, { useState, useEffect, useCallback, forwardRef, useImperativeHandle, useMemo } from 'react';
import styled from 'styled-components';
import { useAuth } from '../../contexts/AuthContext'; // Import useAuth
import raiAPIClient from '../../api/rai_api'; // Keep for delete action

// --- Type Definitions ---

interface ChatItem {
  id: string;
  name: string;
  isPlaceholder?: boolean; // Optional placeholder flag
}

// Props expected by ChatLibrary
interface ChatLibraryProps {
  isOpen: boolean;
  onSelectChat: (sessionId: string) => void | Promise<void>;
  currentSessionId: string; // SessionId is string
  onNewChat: () => void;
  // refreshKey removed - now uses AuthContext
  onChatDeleted: (deletedSessionId: string) => void;
}

// Methods exposed via the ref - DEFINED AND EXPORTED HERE
export interface ChatLibraryRefMethods { // Export the interface
  addPlaceholder: (tempId: string, initialTitle: string) => void;
  confirmPlaceholder: (tempId: string, realSessionData: { id: string; title: string }) => void;
  removePlaceholder: (tempId: string) => void;
}

// Type for styled-component props
interface LibraryContainerProps {
  $isOpen: boolean;
}

interface ChatListProps {
    $isOpen: boolean;
}

interface ChatListItemProps {
  $isPlaceholder?: boolean;
}

interface DeleteButtonProps {
    $isPlaceholder?: boolean;
}

interface NewChatButtonProps {
    $isOpen: boolean;
}

// window.api types are now defined globally in src/types/electron.d.ts


// Placeholder theme - ideally import from App.tsx or a shared theme file
// Add basic type for the theme object
interface Theme {
  colors: {
    background: string;
    text: string;
    accent: string;
    hover: string;
    border: string;
  };
  spacing: {
    sm: string;
    md: string;
  };
  borderRadius: {
    md: string;
  };
  transitions: {
    normal: string;
    fast: string;
  };
}

const theme: Theme = {
  colors: {
    background: '#1a1a1a',
    text: '#ffffff',
    accent: '#3b82f6',
    hover: 'rgba(255, 255, 255, 0.1)',
    border: '#2a2a2a',
  },
  spacing: {
    sm: '8px',
    md: '16px',
  },
  borderRadius: {
    md: '8px',
  },
  transitions: {
    normal: '0.3s ease',
    fast: '0.15s ease',
  },
};

const LibraryContainer = styled.div<LibraryContainerProps>`
  position: absolute; /* Position absolutely */
  left: 0;
  top: 0;
  height: 100vh; /* Use viewport height */
  width: 250px; /* Fixed width */
  background-color: rgba(24, 24, 24, 0.8); /* Slightly more opaque background */
  border-right: 1px solid ${props => props.$isOpen ? theme.colors.border : 'transparent'};
  display: flex;
  flex-direction: column;
  padding: ${theme.spacing.md};
  padding-top: calc(46px + ${theme.spacing.md}); /* Account for title bar */
  padding-bottom: ${theme.spacing.md}; /* Add back standard bottom padding */
  z-index: 150; /* Below TitleBar (200), above default content */
  backdrop-filter: blur(10px);
  white-space: nowrap; /* Prevent content wrapping during transition */
  box-sizing: border-box; /* Ensure padding included in 100vh */

  /* Use transform for sliding animation */
  transform: translateX(${props => props.$isOpen ? '0' : '-100%'});
  transition: transform ${theme.transitions.normal}, padding ${theme.transitions.normal}, border-color ${theme.transitions.normal}; /* Combine transitions */
`;


const ChatList = styled.ul<ChatListProps>`
  list-style: none;
  padding: 0;
  margin: 0;
  overflow-y: auto;
  /* Calculate height based on parent padding and button */
  height: calc(100% - 52px - ${theme.spacing.md}); /* Height minus button area and bottom padding */
  opacity: ${props => props.$isOpen ? 1 : 0}; /* Fade content */
  transition: opacity ${theme.transitions.fast}; /* Add transition for opacity */

  /* Hide scrollbar */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
  &::-webkit-scrollbar {
    display: none; /* Chrome, Safari, Opera */
  }
`;

const ChatListItem = styled.li<ChatListItemProps>`
  display: flex; /* Use flexbox */
  justify-content: space-between; /* Push button to the right */
  align-items: center; /* Vertically align items */
  padding: ${theme.spacing.sm} ${theme.spacing.md};
  margin-bottom: ${theme.spacing.sm};
  border-radius: ${theme.borderRadius.md};
  cursor: ${props => props.$isPlaceholder ? 'default' : 'pointer'}; /* No pointer for placeholders */
  opacity: ${props => props.$isPlaceholder ? 0.6 : 1}; /* Dim placeholders */
  white-space: nowrap;
  overflow: hidden; /* Keep this for the container */
  transition: background-color ${theme.transitions.fast}; /* Faster transition */

  &:hover {
    background-color: ${theme.colors.hover};
  }

  &.active {
    background-color: rgba(255, 255, 255, 0.15); /* Changed to grey highlight */
    font-weight: 500;
  }
`;

// New Delete Button for list items
const DeleteButton = styled.button<DeleteButtonProps>`
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  font-size: 14px; /* Smaller size */
  font-weight: bold;
  cursor: pointer;
  padding: 0 4px; /* Minimal padding */
  margin-left: ${theme.spacing.sm};
  opacity: ${props => props.$isPlaceholder ? 0 : 0}; /* Hidden by default and always hidden for placeholders */
  pointer-events: ${props => props.$isPlaceholder ? 'none' : 'auto'}; /* Disable clicks for placeholders */
  transition: opacity ${theme.transitions.fast}, color ${theme.transitions.fast};

  ${ChatListItem}:hover & {
    opacity: 1; /* Show on hover of the list item */
  }

  &:hover {
    color: rgba(255, 100, 100, 0.8); /* Reddish on hover */
  }

  &:focus {
    outline: none;
  }
`;


const NewChatButton = styled.button<NewChatButtonProps>`
    /* Style similar to IconButton in App.jsx */
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.2);
    background-color: transparent;
    color: ${theme.colors.text};
    font-size: 20px; /* Larger '+' */
    font-weight: 300;
    cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'}; /* Indicate disabled state */
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all ${theme.transitions.fast};
    flex-shrink: 0; /* Prevent shrinking */
    margin-bottom: ${theme.spacing.md}; /* Add space below button */
    align-self: flex-start; /* Align button to the left */
    opacity: ${props => props.$isOpen ? (props.disabled ? 0.5 : 1) : 0}; /* Dim if disabled */
    pointer-events: ${props => props.$isOpen ? 'auto' : 'none'};
    transition: opacity ${theme.transitions.fast}, border-color ${theme.transitions.fast}, background-color ${theme.transitions.fast};

    &:hover {
        background-color: ${props => props.disabled ? 'transparent' : 'rgba(255, 255, 255, 0.05)'};
        border-color: ${props => props.disabled ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.4)'};
    }

    &:focus {
        outline: none;
        border-color: ${props => props.disabled ? 'rgba(255, 255, 255, 0.2)' : theme.colors.accent};
    }
`;


// --- Component ---
// Use React.forwardRef with explicit types for props and ref methods
const ChatLibrary = forwardRef<ChatLibraryRefMethods, ChatLibraryProps>(
    ({ isOpen, onSelectChat, currentSessionId, onNewChat, /* refreshKey removed */ onChatDeleted }, ref) => {
  // Use window.api.logToFile if available, otherwise fallback to console.log
  const log = console.log; // Use console.log for web
  // Get session data and loading status from AuthContext
  const { sessions, isFetchingSessions, error: authError, fetchUserSessions } = useAuth(); // Added fetchUserSessions
  // Local state only for placeholder management
  const [localChats, setLocalChats] = useState<ChatItem[]>([]); // Local copy for optimistic updates
  const [hasActivePlaceholder, setHasActivePlaceholder] = useState<boolean>(false);
  log(`ChatLibrary Render: isFetchingSessions=${isFetchingSessions}, contextSessionsCount=${sessions?.length ?? 'null'}, localChatsCount=${localChats.length}, authError=${authError}, hasActivePlaceholder=${hasActivePlaceholder}, isOpen=${isOpen}`);

  // Effect to synchronize localChats with sessions from context
  useEffect(() => {
    // DETAILED LOGGING BEFORE CHECK:
    log(`>>> ChatLibrary: useEffect[sessions] triggered. typeof sessions: ${typeof sessions}, Array.isArray(sessions): ${Array.isArray(sessions)}, value: ${JSON.stringify(sessions)}`);
    log(`ChatLibrary: useEffect[sessions] triggered. Context sessions count: ${sessions?.length ?? 'null'}, isArray: ${Array.isArray(sessions)}`); // Keep existing log too
    // Add explicit check if sessions is an array
    if (sessions && Array.isArray(sessions)) {
      // Map context sessions to ChatItem format
      const contextChats = sessions.map(s => ({
        id: s.id,
        name: s.title || `Chat ${s.id}` // Use title or fallback
      }));
      // Merge context chats with any existing local placeholder
      setLocalChats(prevLocalChats => {
        const placeholder = prevLocalChats.find(c => c.isPlaceholder);
        const merged = placeholder ? [placeholder, ...contextChats] : contextChats;
        log(`ChatLibrary: Synchronizing localChats. Merged count: ${merged.length}`);
        return merged;
      });
    } else if (!isFetchingSessions) {
        // If sessions are null and not fetching, clear local chats (e.g., after logout or error)
        log(`ChatLibrary: Context sessions are null and not fetching, clearing localChats.`);
        setLocalChats([]);
    }
  }, [sessions, isFetchingSessions, log]); // Depend on sessions from context and loading state


  // --- Imperative Handle for Optimistic Updates ---
  useImperativeHandle(ref, (): ChatLibraryRefMethods => ({
    addPlaceholder(tempId: string, initialTitle: string) {
      log(`ChatLibrary: addPlaceholder called (tempId: ${tempId})`);
      if (hasActivePlaceholder) {
          log(`ChatLibrary: addPlaceholder - SKIPPING, placeholder already active.`);
          return;
      }
      const placeholder: ChatItem = {
        id: tempId,
        name: initialTitle || "New Chat...",
        isPlaceholder: true,
      };
      log(`>>> ChatLibrary: addPlaceholder called (tempId: ${tempId}). Setting local state...`);
      // Add placeholder to local state for immediate UI update
      setLocalChats(prevChats => [placeholder, ...prevChats.filter(c => !c.isPlaceholder)]);
      setHasActivePlaceholder(true);
      log(`>>> ChatLibrary: addPlaceholder - setHasActivePlaceholder(true) called.`);
    },
    confirmPlaceholder(tempId: string, realSessionData: { id: string; title: string }) {
      log(`ChatLibrary: confirmPlaceholder called (tempId: ${tempId}, realId: ${realSessionData.id})`);
      // Remove placeholder and reset flag *before* fetching
      setLocalChats(prevChats => prevChats.filter(chat => chat.id !== tempId));
      setHasActivePlaceholder(false);
      log(`>>> ChatLibrary: confirmPlaceholder - Placeholder removed, hasActivePlaceholder=false.`);
      
      // Add a delay to ensure the backend has enough time to save the session before fetching
      setTimeout(() => {
        log(`>>> ChatLibrary: Triggering session fetch after new chat creation (${realSessionData.id})`);
        fetchUserSessions(); // Call fetchUserSessions from AuthContext with a delay
      }, 500);
    },
    removePlaceholder(tempId: string) {
      log(`ChatLibrary: removePlaceholder called (tempId: ${tempId})`);
      setLocalChats(prevChats => prevChats.filter(chat => chat.id !== tempId));
      setHasActivePlaceholder(false);
      log(`>>> ChatLibrary: removePlaceholder - Placeholder removed, hasActivePlaceholder=false.`);
      // Optionally trigger a fetch if needed, though likely not necessary if chat creation failed
      // fetchUserSessions();
    }
  }));
  // --- End Imperative Handle ---

  const handleSelect = (chat: ChatItem) => {
    if (chat.isPlaceholder || chat.id.startsWith('temp-')) {
        log(`ChatLibrary: Prevented selection of placeholder chat (ID: ${chat.id})`);
        return;
    }
    if (onSelectChat) {
      onSelectChat(chat.id);
    }
  };

  const handleNewChatClick = () => {
    if (hasActivePlaceholder) {
        log("ChatLibrary: New chat creation blocked, placeholder active.");
        alert("Please wait for the current new chat to be created before starting another.");
        return;
    }
    if (onNewChat) {
        onNewChat();
    }
  };

  // --- Delete Chat Handler ---
  const handleDeleteChat = async (chatId: string, chatName: string) => {
    // Bypass confirmation dialog - always proceed with deletion
    // Original code: if (!window.confirm(`Are you sure you want to delete the chat "${chatName}"? This cannot be undone.`)) {
    //   return;
    // }

    log(`Attempting to delete chat: ${chatId}`);
    try {
      // Use raiAPIClient directly
      const apiResponse = await raiAPIClient.deleteChatSession(chatId);
      log(`Delete response for ${chatId}: ${JSON.stringify(apiResponse)}`);

      if (apiResponse && (apiResponse.status === 'success' || apiResponse.status === 'partial_success')) {
        // Trigger refresh via AuthContext
        fetchUserSessions();
        // Notify parent component
        if (onChatDeleted) {
          onChatDeleted(chatId);
        }
      } else {
        throw new Error(apiResponse?.error || 'Failed to delete session');
      }
    } catch (err: any) {
      log(`ERROR: Failed to delete chat ${chatId}: ${err.message || err}`);
      alert(`Error deleting chat: ${err.message || 'Unknown error'}`);
      // Optionally trigger a refresh even on error to sync state
      fetchUserSessions();
    }
  };
  // --- End Delete Chat Handler ---


  return (
    <> {/* Fragment starts here */}
      <LibraryContainer $isOpen={isOpen}>
          <NewChatButton
              $isOpen={isOpen}
              onClick={handleNewChatClick}
              disabled={hasActivePlaceholder} // Disable if placeholder exists
              title="Start New Chat"
          >
              +
          </NewChatButton>
          <ChatList $isOpen={isOpen}>
              {/* Display Loading or Error State from AuthContext */}
              {isFetchingSessions && <ChatListItem $isPlaceholder>Loading chats...</ChatListItem>}
              {!isFetchingSessions && authError && <ChatListItem $isPlaceholder style={{ color: 'red' }}>{authError}</ChatListItem>}

              {/* Display chats derived from context, managed by localChats for optimistic updates */}
              {!isFetchingSessions && !authError && localChats.length === 0 && <ChatListItem $isPlaceholder>No chats yet.</ChatListItem>}
              {!isFetchingSessions && !authError && localChats.map(chat => (
                <ChatListItem
                  key={chat.id}
                  onClick={() => handleSelect(chat)}
                  className={currentSessionId === chat.id ? 'active' : ''}
                  title={chat.name}
                  $isPlaceholder={chat.isPlaceholder}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {chat.name}
                  </span>
                  {!chat.isPlaceholder && (
                    <DeleteButton
                        $isPlaceholder={chat.isPlaceholder}
                        onClick={(e: React.MouseEvent<HTMLButtonElement>) => { // Type the event
                            e.stopPropagation(); // Prevent triggering handleSelect
                            handleDeleteChat(chat.id, chat.name);
                        }}
                        title={`Delete chat: ${chat.name}`}
                    >
                        ✕
                    </DeleteButton>
                  )}
                </ChatListItem>
              ))}
          </ChatList>
       </LibraryContainer>
    </>
  ); // Closing parenthesis for return
}); // Closing parenthesis and brace for forwardRef

export default ChatLibrary;