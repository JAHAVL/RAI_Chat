# RAI_Chat Module

The RAI_Chat module is the core component of the AI Assistant app that provides the chat functionality. It contains all the components necessary for managing conversations, memory, and user interactions.

## Components

### Memory Management

The memory management system is organized in the `memory` folder and includes:

- **Memory Manager**: Manages different types of memory for the AI assistant
- **Contextual Memory Manager**: Provides a three-tier memory system for maintaining context
- **Episodic Memory Manager**: Handles information from past conversations

### Conversation Management

The conversation management components include:

- **Conversation Manager**: Manages conversation flow, history, and state

### User Interface

The user interface components are organized in the `ui` folder and include:

- **Chat UI**: User interface components for the chat experience
- **Chat Library UI**: Library components for the chat UI
- **Chat Library UI API**: API for the chat library UI components
- **UI Manager**: Manages the overall user interface
- **UI Manager API**: Provides API endpoints for UI management

### Authentication

The module now includes components for user authentication and session management:

- **Auth DB (`auth_db.py`)**: Handles SQLite database operations for storing and verifying user credentials (username, hashed password).
- **User Session Manager (`user_session_manager.py`)**: Manages the instantiation and caching of user-scoped managers (ChatFileManager, ContextualMemoryManager, EpisodicMemoryManager) based on the authenticated user ID. Ensures data isolation between users.
- **API Endpoints (`rai_api_server.py`)**: Provides `/api/auth/register` and `/api/auth/login` endpoints. Protects other endpoints using JWT authentication.

### LLM Integration

The LLM (Language Learning Model) integration is handled through:

- **LLM API Bridge (`llm_Engine/llm_api_bridge.py`)**: Connects to the separate LLM API Server.

### Data Storage

The module includes storage for chat-related data:

- **Chats**: Contains JSON files with chat history
- **Conversations**: Contains JSON files with conversation data

## Integration

The RAI_Chat module integrates with other components of the application through the API Gateway. It provides a comprehensive solution for managing conversations, storing and retrieving memory, and delivering a seamless chat experience.

## Recent Fixes & Key Functionality Notes (March 31, 2025)

Several issues related to chat session loading and creation after the introduction of user authentication were resolved. Here's a summary of the key fixes and how the system now works:

1.  **Backend Chat Saving:**
    *   **Problem:** New chats were not being saved because the `/api/chat` endpoint incorrectly returned `"status": "error"` due to a mismatch in the expected response structure from `ConversationManager`. This prevented the save logic from executing.
    *   **Fix:** `ConversationManager.get_response` was modified to return the full structured dictionary received from the LLM, allowing the `/api/chat` endpoint to correctly parse it, set `"status": "success"`, and trigger the `save_current_chat` function.
    *   **Result:** New chats are now reliably saved to the user-specific directory (`data/{user_id}/chats/`).

2.  **Loading Existing Chats:**
    *   **Problem:** Existing chats created before user authentication were not loading because they resided in the old `RAI_Chat/chats/` directory, while the system (correctly) looked in the user-specific `data/{user_id}/chats/` directory.
    *   **Fix:** Pre-existing chat files were manually migrated to the appropriate user directory (e.g., `data/1/chats/`).
    *   **Result:** Existing chats now load correctly for the associated user.

3.  **Frontend API Port:**
    *   **Problem:** The frontend API client (`frontend/src/api/rai_api.js`) was configured to connect to the wrong port (5001 instead of 5002).
    *   **Fix:** The `API_BASE_URL` in `rai_api.js` was corrected to `http://localhost:5002/api`.
    *   **Result:** The frontend can now successfully communicate with the backend API.

4.  **Initial Chat List Load:**
    *   **Problem:** The chat list (`ChatLibrary`) might not load immediately after login because the component mounted without a specific trigger to fetch the list.
    *   **Fix:** An `useEffect` hook was added to `AppLayout` in `frontend/src/App.jsx` that increments a `refreshCounter` state variable upon mounting. This counter is passed as `refreshKey` to `ChatLibrary`, triggering its initial `fetchChats` call.
    *   **Result:** The chat list is fetched and displayed promptly after login.

5.  **Optimistic UI for New Chats:**
    *   **Problem:** New chats added optimistically to the frontend (`ChatLibrary`) would disappear because background refreshes (`fetchChats`) would overwrite the local state before the new chat was confirmed and saved by the backend. Various attempts to pause fetching or merge states were overly complex.
    *   **Fix:**
        *   The `fetchChats` logic in `ChatLibrary.jsx` was updated to intelligently merge the fetched list from the backend with any *active* placeholder currently in the local state. It preserves the placeholder until it's confirmed or removed.
        *   The call to trigger a refresh (`onNewSessionCreated` -> increments `refreshCounter`) was restored in `AppContent.jsx` *after* the optimistic confirmation (`onConfirmNewChat`) completes. This ensures `fetchChats` runs *after* the placeholder is confirmed locally, allowing the merge logic to correctly incorporate the now-saved chat from the backend list.
    *   **Result:** New chats appear immediately as placeholders and persist correctly after the backend response.

## RESTful API Architecture

The module follows a RESTful API architecture that:

1. Separates frontend from backend
2. Implements a modular approach where components connect through APIs
3. Supports future migration of LLM to a separate server
4. Maintains session management across all APIs

## File Structure

```
RAI_Chat/
├── __init__.py
├── auth_db.py                  # User credential database handling
├── conversation_manager.py     # Manages conversation flow for a user session
├── prompts.py                  # System prompt generation logic
├── rai_api_server.py           # Main Flask API server for this module
├── user_session_manager.py     # Manages user-scoped manager instances
├── frontend/                   # React frontend source code
│   ├── public/
│   ├── src/
│   │   ├── api/                # Frontend API client (rai_api.js)
│   │   ├── components/         # Reusable UI components (including auth/)
│   │   ├── context/            # React Context providers (AppContext, AuthContext)
│   │   ├── modules/            # Feature-specific UI modules (chat, chat_library)
│   │   ├── App.jsx             # Main application component
│   │   └── index.jsx           # Entry point
│   ├── package.json
│   └── ...
├── memory/                     # Memory management components (user-scoped)
│   ├── __init__.py
│   ├── contextual_memory.py    # Manages active conversation context
│   ├── episodic_memory.py      # Manages long-term episodic memory
│   └── README.md
├── utils/                      # Utility modules
│   └── chat_file_manager.py    # Handles loading/saving chat files (user-scoped)
└── README.md                   # This documentation
```
