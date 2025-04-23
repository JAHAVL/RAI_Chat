const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

// Disable hardware acceleration
app.disableHardwareAcceleration();

function createWindow() {
  // Create the browser window
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
      webSecurity: false,
    },
  });

  // Load the test-simple.html file
  const htmlPath = path.join(__dirname, 'public/test-simple.html');
  const fileUrl = `file://${htmlPath}`;
  
  console.log('Loading HTML from:', fileUrl);
  console.log('File exists:', fs.existsSync(htmlPath));
  
  mainWindow.loadURL(fileUrl);

  // Open DevTools
  mainWindow.webContents.openDevTools();

  // Add error handler for page load failures
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load:', errorCode, errorDescription);
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});