/**
 * Shared theme definition for all modules
 * This file defines the common styling elements used across the application
 */

export const theme = {
  colors: {
    background: '#121212',
    text: '#ffffff',
    accent: '#3b82f6',
    hover: 'rgba(59, 130, 246, 0.1)',
    userMessage: 'rgba(59, 130, 246, 0.25)',
    assistantMessage: '#1e1e1e',
    systemMessage: '#2a2a2a',
    border: '#2a2a2a',
    inputBackground: '#1a1a1a',
    shadow: 'rgba(0, 0, 0, 0.5)',
    placeholder: '#888888'
  },
  sizes: {
    minWidth: '250px',
    defaultWidth: '300px',
    maxWidth: '1200px',
    minHeight: '400px',
    defaultHeight: '600px',
    messagePadding: '10px',
    iconSize: '18px',
    inputHeight: '50px'
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px'
  },
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '16px',
    full: '9999px',
    userMessage: '16px 16px 0 16px',
    assistantMessage: '16px 16px 16px 0'
  },
  typography: {
    fontFamily: "'Inter', sans-serif", // Added fontFamily
    fontSize: {
      xs: '10px',
      sm: '12px',
      md: '14px',
      lg: '16px',
      xl: '20px'
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      bold: 700
    },
    lineHeight: {
      tight: 1.2,
      normal: 1.5,
      relaxed: 1.7 // Renamed from loose and updated value
    }
  },
  transitions: {
    fast: '0.1s ease',
    normal: '0.2s ease',
    slow: '0.3s ease'
  },
  zIndex: {
    base: 1,
    dropdown: 100,
    modal: 200,
    tooltip: 300
  },
  shadows: { // Added shadows property
    sm: '0 1px 3px rgba(0, 0, 0, 0.1)',
    md: '0 4px 6px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px rgba(0, 0, 0, 0.1)'
  }
};

export type Theme = typeof theme;
