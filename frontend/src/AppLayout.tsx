import React, { useState, useRef, useEffect } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import { FaCode, FaVideo } from 'react-icons/fa'; // Icons for module buttons
import HeaderComponent from './pages/Main_Chat_UI/components/HeaderComponent';
import SidebarComponent from './pages/Main_Chat_UI/components/Sidebar';

import { useAuth } from './contexts/AuthContext';
import { useApp } from './contexts/AppContext';
// Import the ChatContext hooks and constants
import { useChat, NEW_CHAT_SESSION_ID, SessionId, initialSystemMessage } from './contexts/ChatContext';
import ChatPage from './pages/Main_Chat_UI/ChatPage';
import { sessionService, chatLibraryService } from './services/chat';
import { moduleService } from './services/app';

import { theme } from '../shared/theme'; // Import the shared theme

// ChatLibraryRefMethods interface definition
export interface ChatLibraryRefMethods {
  addPlaceholder: (tempId: string, initialTitle: string) => void;
  confirmPlaceholder: (tempId: string, realSessionData: { id: string; title: string }) => void;
  removePlaceholder: (tempId: string) => void;
  fetchSessions: () => void;
}

// --- Global Styles ---
export const GlobalStyle = createGlobalStyle`
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    margin: 0; 
    padding: 0; 
    font-family: ${theme.typography.fontFamily};
    background-color: transparent; 
    color: ${theme.colors.text};
    line-height: ${theme.typography.lineHeight.normal};
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    overflow: hidden; 
  }
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.3); }

  #root { 
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }

  code { 
    font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace;
    background-color: rgba(30, 30, 30, 0.6);
    padding: 2px 4px;
    border-radius: 4px;
  }

  /* For Firefox scrollbar (already present in index.css, ensuring it's here) */
  * {
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
  }

  @keyframes fadeIn { 
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

// --- Styled Components ---
const Container = styled.div`
  height: 100vh;
  width: 100vw; 
  margin: 0; 
  padding: 0; 
  overflow: hidden; 
  background-color: rgba(18, 18, 18, 0.3);
  color: ${theme.colors.text};
  position: relative;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(15px);
`;
const MainArea = styled.div`
  display: flex; flex: 1; min-height: 0; 
  position: relative; 
`;
const Content = styled.div`
  flex: 1; position: relative; background-color: transparent; overflow: hidden;
  display: flex; flex-direction: column; padding-top: 46px; 
`;

// --- App Layout Component ---
const AppLayout: React.FC = () => {
  // Use App context for app-level state like activeModule
  const { state: appState, dispatch: appDispatch } = useApp();
  // Use Chat context for chat-related state
  const { state: chatState, dispatch: chatDispatch, createNewChat, setCurrentSession } = useChat();
  
  const { logout } = useAuth(); 
  const { token } = useAuth(); 
  const [currentSessionId, setCurrentSessionId] = useState<SessionId>(NEW_CHAT_SESSION_ID); 
  const [isChatLibraryOpen, setIsChatLibraryOpen] = useState(true); 
  const chatLibraryRef = useRef<ChatLibraryRefMethods>(null); 

  useEffect(() => {
    if (token) { 
      // triggerChatListRefresh(); 
      // log("AppLayout: Token present.");
    } else {
      // log("AppLayout: Token absent.");
    }
  }, [token]); 

  const handleSelectChat = async (sessionId: string) => { 
    // Call sessionService.selectSession with the sessionId and UI update function
    await sessionService.selectSession(
      sessionId,
      setCurrentSessionId
    );
    
    // Also update the ChatContext if needed
    setCurrentSession(sessionId);
  };

  const handleNewChat = () => {
    // Create a new chat
    createNewChat();
    setCurrentSessionId(NEW_CHAT_SESSION_ID);
  };

  const handleChatDeleted = (deletedSessionId: string) => {
    // Handle chat deletion with the sessionService
    sessionService.handleSessionDeletion(
      deletedSessionId,
      currentSessionId,
      setCurrentSessionId
    );
    
    // Also update the ChatContext if needed
    if (deletedSessionId === currentSessionId) {
      createNewChat();
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

  return (
    <>
      <Container>
        <HeaderComponent
          onToggleChatLibrary={() => {
            const newValue = !isChatLibraryOpen;
            setIsChatLibraryOpen(newValue);
          }}
          logout={logout}
        />
        <MainArea>
          <Content>
            <ChatPage
              currentSessionId={currentSessionId}
              setCurrentSessionId={setCurrentSessionId}
              onNewChatPlaceholder={handleNewChatPlaceholder}
              onConfirmNewChat={handleConfirmNewChat}
              onFailedNewChat={handleFailedNewChat}
              isChatLibraryOpen={isChatLibraryOpen}
              setIsChatLibraryOpen={setIsChatLibraryOpen}
            />
          </Content>
          <SidebarComponent
            activeModule={appState.activeModule}
            onModuleChange={(module: string | null) => moduleService.changeActiveModule(module, appDispatch)} 
            moduleButtons={moduleService.getAvailableModules().map(module => {
              const icons = {
                'code': <FaCode />,
                'video': <FaVideo />
              };
              return {
                id: module.id,
                title: module.title,
                icon: icons[module.id as keyof typeof icons]
              };
            })}
          />
        </MainArea>
      </Container>
    </>
  );
};

export default AppLayout;