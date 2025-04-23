import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext'; // Path relative to src
import AuthPage from './pages/Login_Page/AuthPage'; // Path relative to src
import AppLayout from './AppLayout'; // Path relative to src

// For development: Always render children without checking authentication
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Bypass authentication check
  return <>{children}</>;
};

// For development: Always redirect to the main app
const LoginPage: React.FC = () => {
  // Always redirect to the main app
  return <Navigate to="/" replace />;
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