# R.ai Chat Application - Stable Version Backup Documentation

## Current Stable State (March 25, 2025)

This document provides a comprehensive backup of the current stable state of the R.ai Chat application, including architecture, UI components, and configuration details.

## Application Overview

The R.ai Chat application is a desktop electron-based chat interface with a modular architecture. It features a minimalist design with carefully balanced transparency settings for optimal usability and performance.

### Key Features

- Modern minimalist UI with dark theme
- Chat message interface with user/assistant message styling
- Modular architecture with separate frontend and backend
- RESTful API design for component communication
- Window transparency optimized for visibility and performance

## UI Configuration

### Window Properties
- **Title**: "R.ai"
- **Window Dimensions**:
  - Default width: 500px
  - Default height: 650px
  - Minimum width: 480px (ensures sidebar visibility)
  - Minimum height: 650px (ensures input field visibility)
  - Maximum width: 800px (maintains readable text lines)
- **Visual Properties**:
  - Background color: #121212 (dark theme)
  - Transparency: Nearly opaque (0.98 opacity)
  - Standard window frame with traffic light buttons (red, yellow, green)

### Chat Interface
- **Message Styling**:
  - User messages: Right-aligned with translucent blue background (rgba(59, 130, 246, 0.2))
  - Assistant messages: Left-aligned with dark gray background (rgba(55, 55, 55, 0.4))
  - System messages: Centered at top
  - Bubble-style message design with rounded corners
- **Input Field**:
  - Font matches message bubbles for visual consistency
  - Auto-resizing capability
  - Enter key sends messages

### Sidebar
- Module buttons for different functions:
  - Video module (🎥)
  - Code module (💻)
  - Document module (📝)
  - Three additional empty module buttons for future expansion

## Technical Implementation

### Electron Configuration
The application uses Electron for desktop functionality with specific configuration:

```javascript
mainWindow = new BrowserWindow({
  width: 500,
  height: 650,
  minWidth: 480,
  minHeight: 650,
  maxWidth: 800,
  backgroundColor: '#121212',
  transparent: false,
  frame: true,
  titleBarStyle: 'default',
  trafficLightPosition: { x: 10, y: 10 },
  title: 'R.ai',
  webPreferences: {
    nodeIntegration: false,
    contextIsolation: true,
    preload: path.join(__dirname, 'preload.js'),
  },
  show: false,
});
```

### Frontend Architecture
- React-based UI with styled-components
- Context API for state management
- Component-based structure for modularity
- CSS-in-JS styling approach

### Backend Architecture
- RESTful API design
- Modular approach with separate endpoints for each feature
- Designed for future migration of LLM to remote server
- Session management across all API endpoints

## Running the Application

### Development Mode
```bash
cd /Users/jordanhardison/CascadeProjects/ai_assistant_app/RAI_Chat/frontend
npm run electron:dev
```

### Production Build
```bash
cd /Users/jordanhardison/CascadeProjects/ai_assistant_app/RAI_Chat/frontend
npm run build
npm run electron
```

## Important Files

- **Main Electron File**: `/RAI_Chat/frontend/electron_app/main.js`
- **React App Entry**: `/RAI_Chat/frontend/src/App.jsx`
- **Theme Configuration**: `/RAI_Chat/frontend/src/styles/theme.ts`
- **Index Entry Point**: `/RAI_Chat/frontend/src/index.tsx`

## Current Limitations and Future Improvements

1. Backend API implementation is not complete and requires further development
2. Module functionality beyond basic UI is pending implementation
3. Window resizing behavior should be tested on different platforms
4. LLM integration is simulated and needs actual implementation

---

This backup documentation represents the stable state of the R.ai Chat application as of March 25, 2025. All UI elements are properly configured, the window appearance is optimized, and the application structure is in place for continued development of backend functionality.
