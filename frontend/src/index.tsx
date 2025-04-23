import React from 'react';
import ReactDOM from 'react-dom/client';
// Removed import './index.css'; - Styles moved to GlobalStyle in AppLayout
import App from './App'; // Removed .tsx extension

const rootElement = document.getElementById('root');

if (rootElement) {
  console.log("--- index.tsx: Found #root element, rendering App ---"); // DEBUG LOG
  const root = ReactDOM.createRoot(rootElement as HTMLElement);
  root.render(
    // <React.StrictMode> {/* Temporarily disabled for debugging blank screen */}
      <App />
    // </React.StrictMode>
  );
} else {
  console.error("--- index.tsx: CRITICAL ERROR - #root element not found in the DOM! ---"); // DEBUG LOG
}

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
