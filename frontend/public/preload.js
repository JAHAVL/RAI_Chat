// Preload script for Electron
// This script runs in the renderer process before web content loads
// It exposes selected Node.js APIs to the renderer process

const { ipcRenderer } = require('electron');

// Since contextIsolation is disabled, we can directly expose APIs to the window object
// This is less secure but necessary for compatibility with our current setup
window.api = {
  // File operations
  openFile: () => ipcRenderer.invoke('file:open'),
  openFolder: () => ipcRenderer.invoke('folder:open'),
  saveFile: (content) => ipcRenderer.invoke('file:save', content),
  saveFileAs: (content) => ipcRenderer.invoke('file:saveAs', content),
  
  // Module system
  getModules: () => ipcRenderer.invoke('modules:get'),
  loadModule: (moduleId) => ipcRenderer.invoke('module:load', moduleId),
  
  // Chat operations
  sendMessage: (message) => ipcRenderer.invoke('chat:send', message),
  getChatSessions: (token) => ipcRenderer.invoke('chat:getSessions', token),
  deleteChatSession: (sessionId, token) => ipcRenderer.invoke('chat:deleteSession', sessionId, token),
  
  // Backend API
  callBackend: (endpoint, method, data, token) =>
    ipcRenderer.invoke('api:call', endpoint, method, data, token),
    
  // App utilities
  minimize: () => ipcRenderer.send('app:minimize'),
  maximize: () => ipcRenderer.send('app:maximize'),
  close: () => ipcRenderer.send('app:close'),

  // --- NEW: Logging ---
  logToFile: (message) => ipcRenderer.send('log-to-file', message)
};

// Also expose the ipcRenderer directly for development purposes
window.ipcRenderer = ipcRenderer;
