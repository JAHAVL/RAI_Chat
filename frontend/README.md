# AI Assistant VS Code Frontend

This is the Electron-based frontend for the AI Assistant application, providing a VS Code-like experience integrated with the existing Python RESTful backend.

## Architecture

- **Electron Main Process (`public/electron.js`)**: Handles window creation, backend process management (in packaged app), and IPC.
- **Renderer Process (`src/App.jsx`, etc.)**: React application implementing the UI, running inside the Electron window.
- **Preload Script (`public/preload.js`)**: Securely bridges the Renderer and Main processes for specific API calls.
- **API Client (`src/api/rai_api.js`)**: Handles communication with the Python RAI API Server, including authentication headers.
- **Auth Components (`src/components/auth/`)**: Contains `Login.tsx`, `Register.tsx`, and `AuthPage.tsx` for the authentication UI.
- **Auth Context (`src/context/AuthContext.tsx`)**: Manages authentication state (token, user info, loading/error status) and provides login/logout/register functions.

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Python backend setup (see main project README.md)

### Installation

From within the `RAI_Chat/frontend` directory:
```bash
# Install dependencies
npm install
```

### Development

The recommended way to run for development is using the main `start_all.py` script from the project root directory. This script handles starting the backend servers and the frontend development environment.

Alternatively, to start only the frontend development server and Electron app (assuming backend servers are already running):
```bash
# From the RAI_Chat/frontend directory
npm run electron:dev
```

### Building

To build the distributable application packages (requires backend to be built first with PyInstaller):
```bash
# From the RAI_Chat/frontend directory
npm run electron:build
```
This creates packages in the `RAI_Chat/frontend/dist` directory.

## Features

- **File Explorer**: Browse and manage files and folders
- **Monaco Editor**: Full VS Code editing experience with syntax highlighting
- **Multi-Tab Editing**: Work with multiple files simultaneously
- **AI Assistant Integration**: Access the AI Assistant directly from the editor
- **User Authentication**: Secure login/registration flow with session persistence using JWT stored in `localStorage`.
- **Optimistic UI for New Chats**: New chat sessions appear immediately in the Chat Library sidebar upon sending the first message, providing instant feedback. This is achieved by:
    1.  Adding a temporary placeholder item to the `ChatLibrary`'s local state (`AppContent` -> `AppLayout` -> `ChatLibrary.addPlaceholder`).
    2.  Updating this placeholder with real data once the backend confirms the new session (`AppContent` -> `AppLayout` -> `ChatLibrary.confirmPlaceholder`).
    3.  Ensuring background refreshes (`ChatLibrary.fetchChats`) correctly merge the backend list with any active placeholder to prevent it from disappearing prematurely.
    4.  Triggering a final refresh (`AppContent.onNewSessionCreated` -> `AppLayout.refreshCounter` -> `ChatLibrary.fetchChats`) after the optimistic confirmation to synchronize with the backend state.

## API Integration

The frontend communicates with the Python backend through RESTful APIs, maintaining the same modular structure:

- `auth`: User registration and login (`/api/auth/register`, `/api/auth/login`)
- `chat`: Chat interactions (requires authentication)
- `sessions`: Chat session listing and history retrieval (requires authentication)
- `memory`: User memory retrieval (requires authentication)
- `code_editor`: Code editing and file management operations (likely requires authentication)
- `llm`: Language model operations (some may require authentication if user-specific)
- `web_search`: Web search functionality
- `calendar`: Calendar management (likely requires authentication)
- `video`: Video processing features (likely requires authentication)

## Technology Stack

- **Electron**: Cross-platform desktop application framework
- **React**: JavaScript library for building user interfaces
- **styled-components**: CSS-in-JS library for styling
- **Axios**: HTTP client for API communication (used by `rai_api.js`)
- **React Context API**: Used for managing global authentication state (`AuthContext`).
## Directory Structure

```
frontend/
├── public/              # Static assets, main process, preload script
│   ├── index.html       # Main HTML template
│   ├── electron.js      # Electron main process script
│   └── preload.js       # Electron preload script
├── src/                 # React application source code
│   ├── App.jsx          # Main React application component
│   ├── index.jsx        # React application entry point
│   ├── api/
│   │   └── rai_api.js   # API client for backend communication
│   ├── components/      # Reusable UI components
│   │   └── auth/        # Authentication specific components
│   │       ├── Login.tsx
│   │       ├── Register.tsx
│   │       └── AuthPage.tsx
│   ├── context/         # React Context providers
│   │   ├── AppContext.jsx
│   │   └── AuthContext.tsx
│   └── modules/         # Feature-specific UI modules
├── build/               # React build output (created by `npm run build`)
├── dist/                # Electron build output (created by `npm run electron:build`)
└── package.json         # Project configuration and dependencies
```
