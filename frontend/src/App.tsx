import React, { useEffect } from 'react';
import { ThemeProvider } from 'styled-components';
import { theme } from '../shared/theme';
import { GlobalStyle } from './AppLayout';
import { AuthProvider } from './contexts/AuthContext';
import AppRouter from './router';
import appInitService from './services/AppInitService';

// Import providers from dedicated context files
import { AppProvider } from './contexts/AppContext';
import { ChatProvider } from './contexts/ChatContext';

/**
 * Main App component - responsible for:
 * 1. Theme and global styles
 * 2. Provider composition
 * 3. App initialization
 * 
 * No business logic should exist here - it's all moved to the respective context providers
 */
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
      <GlobalStyle />
      <AuthProvider>
        <AppProvider>
          <ChatProvider>
            <AppRouter />
          </ChatProvider>
        </AppProvider>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
