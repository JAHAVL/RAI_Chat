/**
 * Development server for the AI Assistant app
 * This file starts a simple express server to serve our modular app
 */
const express = require('express');
const path = require('path');
const app = express();
const port = 3000;

// Serve static files from the frontend directory
app.use(express.static(path.join(__dirname)));

// Serve the shared theme as a module
app.use('/shared', express.static(path.join(__dirname, 'shared')));

// Set up route to discover modules
app.get('/modules', (req, res) => {
  // In a real implementation, this would dynamically discover modules
  // For now, we'll return hardcoded modules for testing
  res.json({
    modules: [
      { id: 'chat', name: 'Chat Assistant', path: '/modules/chat_module' },
      { id: 'video', name: 'Video Assistant', path: '/modules/video_module' },
      { id: 'code-editor', name: 'Code Editor', path: '/modules/code_editor_module' }
    ]
  });
});

// Serve module directories
app.use('/modules', express.static(path.join(__dirname, '../../modules')));

// Serve index.html for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Start the server
app.listen(port, () => {
  console.log(`AI Assistant app running at http://localhost:${port}`);
});
