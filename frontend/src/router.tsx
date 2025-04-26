import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext'; // Path relative to src
import AuthPage from './pages/Login_Page/AuthPage'; // Path relative to src
import AppLayout from './AppLayout'; // Path relative to src

// Check if user is authenticated before allowing access to a route
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// The actual login page component - no auto-redirect
const LoginPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  
  // If already logged in, redirect to main app
  if (isAuthenticated()) {
    return <Navigate to="/" replace />;
  }
  
  // Otherwise show the auth page
  return <AuthPage />;
};

const AppRouter: React.FC = () => {
  return (
    <HashRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*" // Match all other paths for the main app layout
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        />
      </Routes>
    </HashRouter>
  );
};

export default AppRouter;