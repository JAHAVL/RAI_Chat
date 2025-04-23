const { app, BrowserWindow, dialog, ipcMain } = require('electron'); // Add ipcMain
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const process = require('process');
const axios = require('axios'); // <-- Import axios
const kill = require('tree-kill'); // For killing process trees
const { exec } = require('child_process'); // Needed for command execution

let mainWindow;
let backendProcess = null;
let logStream = null; // Variable to hold the log file stream

// Define Backend API URL (should match rai_api_server.py)
const API_BASE_URL = 'http://localhost:6102/api';

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 500,
    height: 650,
    minWidth: 480, // Updated to match requirements
    minHeight: 650, // Updated to match requirements
    maxWidth: 800,
    backgroundColor: '#121212', // Solid background color matching the app theme
    transparent: false, // Disable transparency completely
    // Removed vibrancy effect which contributes to excess transparency
    frame: true, // Standard window frame with title bar
    titleBarStyle: 'default', // Standard title bar with traffic light buttons
    trafficLightPosition: { x: 10, y: 10 }, // Position the traffic light buttons appropriately
    title: 'R.ai', // Set window title
    webPreferences: {
      nodeIntegration: true, // Enable Node integration for development
      contextIsolation: false, // Disable context isolation for development
      enableRemoteModule: true, // Enable remote module
      webSecurity: false, // Disable web security for development
      preload: path.join(__dirname, 'preload.js'), // Path relative to electron.js in build/
    },
    show: false, // Don't show until ready-to-show
  });

  // Load the index.html from either the dev server or the built app
  const devServerUrl = 'http://localhost:3003'; // Dev server port
  const fileUrl = `file://${path.join(__dirname, '../build/index.html')}`;
  const loadUrl = !app.isPackaged ? devServerUrl : fileUrl;
  
  console.log('App is packaged:', app.isPackaged);
  console.log('Loading URL:', loadUrl);
    
    // Check if the webpack dev server is running
    if (!app.isPackaged) {
      console.log('Checking if webpack dev server is running at:', devServerUrl);
      axios.get(devServerUrl, { timeout: 2000 })
        .then(() => {
          console.log('Webpack dev server is running, loading from:', devServerUrl);
          mainWindow.loadURL(devServerUrl);
        })
        .catch(error => {
          console.error('Webpack dev server is not running:', error.message);
            console.log('Falling back to file URL:', fileUrl);
            
            // Check if the file exists
            const indexPath = path.join(__dirname, '../build/index.html');
            if (fs.existsSync(indexPath)) {
              console.log('index.html exists at:', indexPath);
              mainWindow.loadURL(fileUrl);
            } else {
              console.error('index.html does not exist at:', indexPath);
              mainWindow.loadURL('data:text/html,<html><body><h2>Error: Cannot load application</h2><p>The webpack dev server is not running and index.html was not found.</p></body></html>');
            }
          });
      } else {
        mainWindow.loadURL(fileUrl);
      }

  // Add listeners for debugging loading issues
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    console.error(`ERROR: Failed to load URL: ${validatedURL}\nError Code: ${errorCode}\nDescription: ${errorDescription}`);
    // Use dialog.showErrorBox for better visibility, especially if console isn't checked
    dialog.showErrorBox('Load Error', `Failed to load URL: ${validatedURL}\nError: ${errorDescription} (${errorCode})`);
  });

  mainWindow.webContents.on('dom-ready', () => {
    // This event fires when the document's frame is finished loading,
    // though resources like images may still be loading.
    // If this doesn't fire, the HTML itself might be the issue.
    console.log('INFO: DOM Ready event fired.');
  });
  // End debugging listeners

  // Open DevTools in development mode
  if (!app.isPackaged) { // Use !app.isPackaged instead of isDev
    mainWindow.webContents.openDevTools();
  }

  // Only show the window once it's ready to prevent flickering
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Handle window closing
  mainWindow.on('close', (event) => {
    // Attempt to signal the original launcher script to shut down servers
    const launcherPid = process.env.LAUNCHER_PID;
    if (launcherPid) {
      console.log(`Window closing, sending SIGTERM to launcher process PID: ${launcherPid}`);
      try {
        // Send SIGTERM to the launcher process
        process.kill(parseInt(launcherPid, 10), 'SIGTERM');
      } catch (err) {
        console.error(`Failed to send SIGTERM to launcher process PID ${launcherPid}:`, err);
      }
    } else {
      console.log('LAUNCHER_PID not found in environment. Cannot signal launcher script.');
    }
    // We don't preventDefault, allow the window to close naturally.
  });

  mainWindow.on('closed', () => {
    // mainWindow = null; // This is handled by the 'close' event now indirectly
    // It's generally safe to keep this, but the 'close' handler is the primary shutdown trigger
    mainWindow = null;
  });

  // Restrict window resizing below the minimum dimensions
  // but also allow users to resize up to the maxWidth
  mainWindow.on('will-resize', (event, newBounds) => {
    const minWidth = 480; // Minimum width for UI elements
    const minHeight = 650; // Minimum height for UI elements

    // Check if the new size is below the minimum
    if (newBounds.width < minWidth || newBounds.height < minHeight) {
      event.preventDefault();

      // If width is below minimum but height is ok
      if (newBounds.width < minWidth && newBounds.height >= minHeight) {
        mainWindow.setSize(minWidth, newBounds.height);
      }
      // If height is below minimum but width is ok
      else if (newBounds.height < minHeight && newBounds.width >= minWidth) {
        mainWindow.setSize(newBounds.width, minHeight);
      }
      // If both are below minimum
      else if (newBounds.width < minWidth && newBounds.height < minHeight) {
        mainWindow.setSize(minWidth, minHeight);
      }
    }

    // Check if the new size exceeds the maximum width
    if (newBounds.width > 800) {
      event.preventDefault();
      mainWindow.setSize(800, newBounds.height);
    }
  });
}

// Function to start the bundled Python backend
function startBackend() {
  if (app.isPackaged) { // Use app.isPackaged instead of !isDev
    console.log('Starting backend process...');
    // Path to the bundled backend executable within the packaged app's resources
    // Assumes the 'dist/AI_Assistant_Backend' folder is copied as an extra resource
    const backendExecutableName = 'AI_Assistant_Backend'; // Adjust if PyInstaller output name differs
    // Path relative to app path (inside Resources)
    const backendDir = path.join(app.getAppPath(), '../AI_Assistant_Backend');
    const backendExePath = path.join(backendDir, backendExecutableName);

    console.log(`Attempting to spawn backend at: ${backendExePath}`);

    try {
      // Define log paths within user data directory
      const userDataPath = app.getPath('userData');
      const backendLogPath = path.join(userDataPath, 'backend_stdout.log');
      const backendErrorLogPath = path.join(userDataPath, 'backend_stderr.log');
      console.log(`Redirecting backend logs to: ${userDataPath}`);

      // Create write streams for logs
      const out = fs.openSync(backendLogPath, 'a');
      const err = fs.openSync(backendErrorLogPath, 'a');

      // Spawn the process with detached stdio and redirect to files
      backendProcess = spawn(backendExePath, [], {
        cwd: backendDir,
        detached: true, // Detach from parent
        stdio: [ 'ignore', out, err ] // Redirect stdout/stderr to files
      });

      // Unref the child process to allow the parent to exit independently
      backendProcess.unref();

      // Log process close/error events to Electron's main log AND show dialog
      backendProcess.on('close', (code) => {
        console.log(`Backend process exited with code ${code}`);
        // Optionally show a dialog if it exits unexpectedly?
        // if (code !== 0) {
        //   dialog.showErrorBox('Backend Exited', `Backend process exited unexpectedly with code ${code}.`);
        // }
        backendProcess = null; // Clear reference
      });

      backendProcess.on('error', (err) => {
        console.error('Failed to start backend process:', err);
        dialog.showErrorBox('Backend Startup Error', `Failed to start backend process: ${err.message}\n\nCheck executable path and permissions.`); // Show error dialog
        backendProcess = null;
      });

      console.log('Backend process spawned successfully.');

    } catch (error) {
       console.error('Error spawning backend process:', error);
       dialog.showErrorBox('Backend Spawn Error', `Error trying to spawn backend process: ${error.message}\n\nPath: ${backendExePath}`); // Show error dialog
    }

  } else {
    console.log('Development mode: Backend should be started manually.');
  }
}

// Create window and start backend when Electron is ready
app.whenReady().then(() => {
    // --- Setup Frontend Logging ---
    const userDataPath = app.getPath('userData');
    const frontendLogPath = path.join(userDataPath, 'frontend_renderer.log');
    // --- Show dialog with userDataPath for debugging ---
    dialog.showMessageBoxSync({
        title: "Log Path Info",
        message: `User Data Path (contains frontend_renderer.log):\n${userDataPath}`
    });
    // --- End Show dialog ---
    // Use a variable to store the path for potential logging later
    let logInitializationMessage = `Initializing frontend log file at: ${frontendLogPath}`;
    try {
      // Use 'a' mode to append to the log file
      logStream = fs.createWriteStream(frontendLogPath, { flags: 'a' });
      const initialLogMessage = `\n--- Electron App Started: ${new Date().toISOString()} ---\n${logInitializationMessage}\n`;
      logStream.write(initialLogMessage); // Write initial message directly

      ipcMain.on('log-to-file', (event, message) => {
        if (logStream && typeof message === 'string') {
          const timestamp = new Date().toISOString();
          // Ensure message ends with a newline
          const formattedMessage = message.endsWith('\n') ? message : message + '\n';
          logStream.write(`[${timestamp}] ${formattedMessage}`);
        }
      });
    } catch (err) {
      // Log error to console AND try to show dialog
      console.error('Failed to open frontend log file stream:', err);
      dialog.showErrorBox('Logging Error', `Failed to open frontend log file: ${frontendLogPath}\nError: ${err.message}`);
      logStream = null; // Ensure logStream is null if opening failed
    }
    // --- End Frontend Logging Setup ---

    // --- IPC Handler for Backend API Calls ---
    ipcMain.handle('api:call', async (event, endpoint, method, data, token) => { // Added token argument
      const url = `${API_BASE_URL}${endpoint}`;
      console.log(`IPC api:call received: ${method} ${url}`, data || '', `Token present: ${!!token}`); // Log token presence

      // Use the token passed from the renderer
      const headers = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      try {
        let response;
        const config = { headers }; // Include headers in config

        switch (method.toUpperCase()) {
          case 'GET':
            response = await axios.get(url, config);
            break;
          case 'POST':
            response = await axios.post(url, data, config);
            break;
          case 'PUT':
            response = await axios.put(url, data, config);
            break;
          case 'DELETE':
            response = await axios.delete(url, config);
            break;
          default:
            throw new Error(`Unsupported HTTP method: ${method}`);
        }

        console.log(`Backend API response for ${method} ${url}: Status ${response.status}`);
        return response.data; // Return the JSON data from the response

      } catch (error) {
        console.error(`Error calling backend API (${method} ${url}):`, error.response?.data || error.message);
        // Rethrow a structured error for the renderer process
        throw {
          message: `API call failed: ${error.message}`,
          status: error.response?.status,
          data: error.response?.data
        };
      }
    });
    // --- End IPC Handler ---

    // --- IPC Handler for getting chat sessions ---
    ipcMain.handle('chat:getSessions', async (event, token) => {
      const url = `${API_BASE_URL}/sessions`; // Assuming backend endpoint is /api/sessions
      console.log(`IPC chat:getSessions received: GET ${url}`);
      
      const headers = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
        console.log('Added Authorization header with token for chat:getSessions');
      } else {
        console.warn('No auth token provided for chat:getSessions');
      }

      try {
        const response = await axios.get(url, { headers });
        console.log(`Backend API response for GET ${url}: Status ${response.status}`);
        // Return a structured success response
        return { status: 'success', sessions: response.data };
      } catch (error) {
        console.error(`Error calling backend API (GET ${url}):`, error.response?.data || error.message);
        // Return a structured error response
        return {
          status: 'error',
          error: error.response?.data?.detail || error.message || 'Failed to fetch sessions',
          statusCode: error.response?.status
        };
      }
    });
    // --- End IPC Handler for getting chat sessions ---

    // --- IPC Handler for deleting a chat session ---
    ipcMain.handle('chat:deleteSession', async (event, sessionId, token) => {
      if (!sessionId) {
        console.error('IPC chat:deleteSession error: No session ID provided.');
        return { status: 'error', error: 'No session ID provided' };
      }
      const url = `${API_BASE_URL}/sessions/${sessionId}`; // Assuming backend endpoint is /api/sessions/{id}
      console.log(`IPC chat:deleteSession received: DELETE ${url}`);
      
      const headers = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
        console.log('Added Authorization header with token for chat:deleteSession');
      } else {
        console.warn('No auth token provided for chat:deleteSession');
      }

      try {
        const response = await axios.delete(url, { headers });
        console.log(`Backend API response for DELETE ${url}: Status ${response.status}`);
        // Return a structured success response (might include details from backend if available)
        return { status: 'success', data: response.data };
      } catch (error) {
        console.error(`Error calling backend API (DELETE ${url}):`, error.response?.data || error.message);
        // Return a structured error response
        return {
          status: 'error',
          error: error.response?.data?.detail || error.message || `Failed to delete session ${sessionId}`,
          statusCode: error.response?.status
        };
      }
    });
    // --- End IPC Handler for deleting a chat session ---

    // --- IPC Handler for sending a chat message ---
    ipcMain.handle('chat:send', async (event, messageData) => {
      // messageData should contain { message: string, session_id: string | null, token: string }
      const { message, session_id, token } = messageData;
      const url = `http://localhost:6102/api/chat`; // Use correct RAI API port 6102
      console.log(`IPC chat:send received: POST ${url}`, { message, session_id }, `Token present: ${!!token}`);

      if (!token) {
        console.error('IPC chat:send error: No auth token provided.');
        return { status: 'error', error: 'Authentication token is missing.' };
      }

      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      };
      const payload = { message, session_id };

      try {
        const response = await axios.post(url, payload, { headers });
        console.log(`Backend API response for POST ${url}: Status ${response.status}`);
        // Return the full response data from the backend
        return response.data; // Assuming backend returns { status: 'success', response: '...', session_id: '...' } etc.
      } catch (error) {
        console.error(`Error calling backend API (POST ${url}):`, error.response?.data || error.message);
        // Return a structured error response matching frontend expectations
        return {
          status: 'error',
          response: error.response?.data?.detail || error.message || 'Failed to send message', // Use 'response' key for error message consistency?
          error: error.response?.data?.detail || error.message || 'Failed to send message', // Keep 'error' key too
          statusCode: error.response?.status
        };
      }
    });
    // --- End IPC Handler for sending a chat message ---

    createWindow();
    startBackend(); // Start the backend
  });

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// On macOS, recreate window when dock icon is clicked and no windows are open
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Helper function to find PID by port (macOS/Linux specific using lsof)
function findPidByPort(port, callback) {
  // lsof -i TCP:<port> -s TCP:LISTEN -t -P
  const command = `lsof -i TCP:${port} -s TCP:LISTEN -t -P`;
  exec(command, (error, stdout, stderr) => {
    if (error) {
      if (error.code === 1 && !stderr) { // lsof returns 1 if not found
        console.log(`No process found listening on port ${port}.`);
        callback(null, null);
        return;
      }
      console.error(`Error finding PID for port ${port}: ${stderr || error.message}`);
      callback(error, null);
      return;
    }
    const pid = stdout.trim();
    if (pid && /^\d+$/.test(pid)) {
      console.log(`Found PID ${pid} listening on port ${port}.`);
      callback(null, parseInt(pid, 10));
    } else {
      console.log(`No process found listening on port ${port} (stdout: ${stdout.trim()}).`);
      callback(null, null);
    }
  });
}

// Helper function to kill a process tree
function killProcessTree(pid, signal = 'SIGTERM') {
  return new Promise((resolve, reject) => {
    if (!pid) {
      resolve(); // No PID to kill
      return;
    }
    console.log(`Attempting to kill process tree for PID: ${pid} with signal: ${signal}`);
    kill(pid, signal, (err) => {
      if (err) {
        if (err.message.includes('No such process')) {
           console.warn(`Process ${pid} likely already terminated.`);
           resolve();
        } else {
           console.error(`Error killing process tree ${pid}:`, err);
           reject(err);
        }
      } else {
        console.log(`Successfully sent ${signal} to process tree ${pid}.`);
        resolve();
      }
    });
  });
}


// Ensure backend process is killed when the app quits
app.on('will-quit', () => {

  // --- Add logic to kill external backend servers ---
  console.log('Attempting to terminate external backend servers...');
  const portsToKill = [6301, 6102]; // LLM and RAI API ports
  const killPromises = portsToKill.map(port => {
    return new Promise((resolve) => { // Simplified: always resolve
      findPidByPort(port, async (err, pid) => {
        if (err) {
          console.error(`Error finding PID for port ${port}:`, err);
        } else if (pid) {
          try {
            await killProcessTree(pid); // Attempt to kill the process tree
          } catch (killErr) {
            console.error(`Error during kill process for PID ${pid} on port ${port}:`, killErr);
          }
        }
        resolve(); // Resolve regardless of find/kill outcome
      });
    });
  });

  // Wait for all kill attempts to settle before proceeding with app quit
  Promise.allSettled(killPromises).then(() => {
      console.log('Finished attempting to terminate external backend servers.');

      // Existing logStream handling and app quit logic should follow here...
      if (logStream) {
        const quitMessage = `--- Electron App Quitting: ${new Date().toISOString()} ---\n`;
        console.log('Closing frontend log stream...');
        logStream.end(quitMessage, () => {});
        logStream = null;
      }
      // Note: app.quit() is implicitly called after 'will-quit' handlers finish
  });
  // --- End logic to kill external backend servers ---

  // Original backendProcess kill logic (only relevant for packaged app)
  if (backendProcess) {
    console.log('Terminating bundled backend process...');
    backendProcess.kill(); // Use simple kill for the direct child
    backendProcess = null;
  }
  // Close the log stream when quitting
  // Original logStream closing logic (now moved inside Promise.allSettled callback)
});
