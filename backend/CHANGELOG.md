# AI Assistant Changelog

## Version 1.3.1 (April 8, 2025)

### Refactoring
- **Frontend TypeScript Conversion:**
  - Converted core frontend files (`App`, `ChatLibrary`, API clients, contexts, utils) from `.jsx`/`.js` to `.tsx`/`.ts`.
  - Installed necessary TypeScript dependencies (`typescript`, `@types/*`).
  - Created `tsconfig.json` for the frontend project.
  - Methodology:
    - Gradually migrated files using `@ts-ignore` and `any` types to minimize initial friction.
    - Incrementally added strict type checking and resolved type errors.
    - Centralized type definitions in dedicated `.d.ts` files for better type management.
    - Leveraged TypeScript's type inference and explicit type annotations to improve code quality.
  - Added type definitions for `styled-components` theme (`types/styled.d.ts`) and Electron preload API (`types/electron.d.ts`).
  - Centralized `Message` type definition (`types/chat.d.ts`).
  - Resolved various type errors and build issues related to the conversion.
- **Legacy Code Removal:**
  - Removed the conflicting legacy `RAI_Chat/memory/memory_manager.py` (backed up outside project) as it was architecturally inconsistent and likely causing state issues.
  - Removed the `modules/video_module/` directory and `api/video_api.py` as they depended on the legacy `MemoryManager`.
  - Updated `utils/module_loader.py`, `api/api_server.py`, `api/api_gateway.py`, `api/gateway.py`, `api/api_client.py`, and relevant `__init__.py` files to remove references to the deleted video module and legacy memory manager.
- **Session Persistence & Loading:**
  - Consolidated session persistence under `ChatFileManager`, making it the single source of truth for chat/metadata files (`chats/metadata_{id}.json`, `chats/{id}.json`).
  - Refactored `ContextualMemoryManager` to load session data on demand via `ChatFileManager` instead of using its own separate persistence file (`contextual_sessions.json`). Removed `save/load_session_memories`.
  - Updated `ConversationManager` save/load logic to handle full turn objects consistently with `ChatFileManager`.
  - Made `ContextualMemoryManager._ensure_session_exists` robust to handle loading potentially old-format session files during transition.
- **Logging:** Corrected root logger configuration in `start_all.py` to include a `FileHandler` (`logs/main_app.log`) alongside the `StreamHandler` for better error tracking. Fixed logging path construction in `ContextualMemoryManager` and `EpisodicMemoryManager`.
- **Chat Functionality:** Resolved silent failure issue after message submission, which was caused by a combination of path inconsistencies in `FileManager`, state conflicts from the legacy `MemoryManager`, and incorrect session loading/saving logic.

## Version 1.3.0 (April 5, 2025)

### Bug Fixes & Improvements

-   **Application Launch:** Replaced unreliable `start_all.py` script with new `Launch_App.py`. The new script uses `subprocess.Popen` for more robust starting of backend servers (LLM API, RAI API) and the frontend (`npm start`), including process monitoring and cleanup on exit.
-   **Login Failure:** Resolved "Invalid username or password" errors caused by a database schema mismatch. The `users` table was missing the `remembered_facts` column. Added the column directly via SQL (`ALTER TABLE`) after encountering issues with Alembic history inconsistency.
-   **Chat Internal Error:** Fixed internal server errors occurring after login when sending chat messages. This involved resolving multiple issues:
    -   Removed incorrect usages of the deprecated `get_user_memory_dir` function in `contextual_memory.py` (`NameError` and `AttributeError`).
    -   Corrected a `TypeError` in `conversation_manager.py` by ensuring the database session was passed correctly to `contextual_memory.process_forget_command`. Updated `rai_api_server.py` to provide the database session to the conversation manager during chat requests.
-   **Database Migrations:** Addressed Alembic configuration issues (`env.py`) to correctly target the MySQL database using the `DATABASE_URL` environment variable, although direct SQL was ultimately used for the schema fix due to history conflicts.

## Version 1.2.9.4 (April 3, 2025)

### Improvements
- **Chat Library Synchronization:**
  - Implemented periodic background polling (every 20 seconds) to keep chat library in sync with backend.
  - Added delayed session fetch mechanism to ensure new chats appear without manual refresh.

### Bug Fixes
- **System Message Handling:**
  - Fixed system message transition from "Searching the web..." to "Searched the web..."
  - Ensured proper state update for assistant messages during web searches.

## Version 1.2.9 (April 2, 2025)

### Features & Enhancements
- **Web Search Integration (Tavily):**
  - Added Tavily API client (`tavily-python`) for web search functionality.
  - Implemented logic in `ConversationManager` to detect a `[SEARCH: query]` command from the LLM.
  - Added `perform_search` function in `RAI_Chat/Built_in_modules/web_search_module/tavily_client.py` to interact with Tavily API.
  - Updated system prompt (`prompts.py`) to instruct the LLM on how and when to use the `[SEARCH:]` command.
  - Added safeguard in `ConversationManager` to display raw search results if the LLM fails to synthesize an answer after searching.
- **API Key Management:**
  - Implemented `.env` file loading for local development API keys (`TAVILY_API_KEY`, `GEMINI_API_KEY`).
  - Created `.env.example` file.
  - Ensured API keys from `.env` are correctly loaded and passed to relevant engine initializers (`GeminiEngine`, `TavilyClient`).
- **Documentation:** Added `web_search_plan.md` outlining the architecture and implementation steps.

### Bug Fixes & Improvements
- **LLM Engine Fallback:** Fixed argument mismatch error when `GeminiEngine` falls back to `MockEngine`.
- **Gemini Engine Initialization:** Resolved issue where `GeminiEngine` failed to find the API key in the LLM API server subprocess by explicitly loading `.env` within the server process.
- **Web Search Loop:** Prevented infinite search loop by refining prompt instructions and adding safeguards in `ConversationManager`.
- **File Structure:** Moved `web_search_module` to `RAI_Chat/Built_in_modules/` and cleaned up old files.

## Version 1.2.8 (March 31, 2025)

### Bug Fixes & Improvements

- **Chat Saving & Loading:**
  - Fixed backend issue where new chats were not saved due to incorrect status reporting in `/api/chat`. `ConversationManager` now returns the full structured response, allowing the API endpoint to correctly set `"status": "success"` and trigger saving.
  - Migrated existing chat files from legacy `RAI_Chat/chats/` directory to user-specific `data/{user_id}/chats/` directory to ensure they load correctly after user authentication implementation.
  - Corrected the frontend API client (`rai_api.js`) to use the correct backend port (5002 instead of 5001).
  - Ensured the chat list (`ChatLibrary`) performs an initial fetch immediately after user login by adding a mount effect trigger in `AppLayout`.
- **Optimistic UI for New Chats:**
  - Resolved issue where new chats added optimistically would disappear. The final fix involves:
    - `ChatLibrary.fetchChats` intelligently merging the backend list with any active local placeholder.
    - Restoring the call to `onNewSessionCreated` in `AppContent` after optimistic confirmation, ensuring `fetchChats` runs again to synchronize the state.
- **Electron Stability:**
  - Fixed an `EPIPE` error that could occur during application shutdown by removing a `console.log` call within the `logStream.end()` callback in `electron.js`.

## Version 1.2.7 (March 30, 2025)

### Standalone Application Build
- **PyInstaller Integration:** Added PyInstaller to bundle the Python backend (`start_all.py` and dependencies) into a standalone executable (`dist/AI_Assistant_Backend`).
- **Electron Builder Configuration:** Configured `electron-builder` in `RAI_Chat/frontend/package.json` to:
  - Use `RAI_Chat/frontend/public/electron.js` as the main process entry point (conforming to `react-cra` preset).
  - Include the PyInstaller-bundled backend (`dist/AI_Assistant_Backend`) as an `extraResource`.
  - Correctly reference the main process file (`"main": "build/electron.js"`).
- **Electron Main Process (`electron.js`) Updates:**
  - Added logic to automatically spawn the bundled Python backend executable when running the packaged app (`app.isPackaged`).
  - Corrected paths for loading the frontend (`index.html`) and the bundled backend executable relative to the packaged app structure (`process.resourcesPath`, `app.getAppPath()`).
  - Replaced `electron-is-dev` with native `app.isPackaged` check.
  - Added error dialogs (`dialog.showErrorBox`) for backend spawn failures.
  - Added logic to terminate the backend process when the Electron app quits.
- **Dependency Management:**
  - Resolved PyInstaller conflict by removing legacy `PyQt5` dependencies from `requirements.txt` and excluding the module during build.
  - Resolved `pip install` errors by regenerating `requirements.txt` without local file paths.
  - Resolved `fsspec` version conflict in `requirements.txt`.
  - Moved `electron` and `electron-builder` from `dependencies` to `devDependencies` in frontend `package.json`.
  - Removed unused `electron-is-dev` dependency.
- **Build Process:** Added `chmod +x` to the build script to ensure backend executable has correct permissions. Added steps to clean `dist` directories before builds.
- **Debugging:** Added extensive logging to backend components (`llm_client.py`, `conversation_manager.py`, `contextual_memory.py`) and frontend API client (`rai_api.js`) to trace prompt generation and session ID handling. Added backend log redirection to user data directory in `electron.js`.

### Bug Fixes
- **Session Handling:** Corrected `rai_api_server.py` to return the actual internal session ID to the client, enabling context persistence across requests.
- **Frontend Session ID:** Modified frontend (`App.jsx`, `rai_api.js`) to correctly store and send the received session ID.
- **Prompt Generation:** Fixed indentation error in `prompts.py` (`build_system_prompt`) that caused `None` to be returned for the system prompt on the first turn. Fixed `conversation_manager.py` to correctly fetch and include contextual memory summary in the prompt.
- **Development Server:** Fixed `ModuleNotFoundError` for `RAI_Chat.ui` in `RAI_Chat/__init__.py` by commenting out legacy UI imports, allowing `start_all.py` to run successfully.
- **Electron Preload Path:** Corrected the path to `preload.js` in `electron.js` after moving the main process file.
- **React Warning:** Fixed styled-components warning by using transient prop (`$active`) for `ModuleButton` in `App.jsx`.

## Version 1.2.6 (March 25, 2025)

### Memory System Enhancements
- **Expanded Working Memory**: Increased working memory capacity from 10 to 50 messages for longer conversation context
- **Enhanced Episodic Memory**: Improved storage and retrieval of personal information in episodic memory
- **Personal Information Extraction**: Added specialized patterns to identify and store user's personal details
- **Intelligent Memory Retrieval**: Enhanced the LLM prompt with relevant memories from past conversations
- **Contextual Session Handling**: Fixed session ID tracking across all components of the architecture
- **Fact-Based Memory System**: Added structured storage of personal facts for consistent retrieval
- **Improved Conversation History**: Better handling of conversation history between RAI API and LLM API
- **Enhanced Memory Relevance**: Added importance scoring for personal facts to prioritize critical information

### Architecture Improvements
- **Consistent Session Management**: Fixed session ID handling across the three-tier architecture
- **Memory Synchronization**: Ensured proper synchronization between working memory and episodic memory
- **Enhanced LLM Client**: Updated LLM client to properly handle and preserve session information
- **Improved Error Logging**: Added better debugging information for memory-related operations

## Version 1.2.5 (March 22, 2025)

### Video Metadata Enhancements
- **Enhanced Video Information Storage**: Added comprehensive metadata storage for videos, including video length, key points count, and reels count
- **Improved Contextual Memory Integration**: Enhanced the storage and retrieval of video information in the contextual memory system
- **Metadata Display in Summaries**: Video summaries now include metadata about the video length, key points, and reels created
- **Reel Count Tracking**: Added automatic updating of reel count when reels are created from a video
- **Better Query Detection**: Improved detection of queries about video metadata such as length, key points, and reels
- **Unified Memory System**: Streamlined video information storage to use the contextual memory system as the primary storage

### Bug Fixes
- **Fixed Key Points Handling**: Resolved issues with key points and key moments being treated inconsistently
- **Improved Error Handling**: Enhanced error handling during video processing and metadata retrieval
- **Better Backward Compatibility**: Maintained compatibility with the legacy memory system while prioritizing the contextual memory system

## Version 1.2.4 (March 21, 2025)

### Episodic Memory Enhancements
- **Improved Travel Memory**: Enhanced detection and relevance scoring for travel-related queries
- **Better Location Recognition**: Added specialized handling for location mentions in conversations
- **Enhanced Result Formatting**: Improved presentation of travel experiences with clearer organization
- **Comprehensive Topic Detection**: Added more robust keyword matching for various categories
- **Normalized Relevance Scoring**: Implemented better scoring system for consistent comparison

### API Connection Improvements
- **Robust Error Handling**: Added retry mechanism with exponential backoff for API requests
- **Enhanced Debugging**: Improved error logging with detailed information for troubleshooting
- **Connection Resilience**: Better handling of timeouts and connection issues with Ollama
- **Consistent API URLs**: Fixed inconsistencies in API endpoint URLs throughout the codebase
- **User-Friendly Error Messages**: More informative error messages when API issues occur

## Version 1.2.3 (March 20, 2025)

### Video Transcript Summarization Fixes
- **Fixed Transcript Summarization**: Replaced non-existent `llm.get_chat_response` method with direct Ollama API implementation
- **Added Fallback Mechanism**: Implemented a robust fallback summary generator when the LLM API is unavailable
- **Enhanced Error Handling**: Improved error handling with timeouts and connection error detection
- **Improved Logging**: Added detailed debug logging throughout the transcript handling process
- **System Message Integration**: Added system messages to notify users when video transcripts are available
- **Updated Documentation**: Enhanced README with comprehensive information about video processing features

## Version 1.2.2 (March 20, 2025)

### Video UI Enhancements
- **Blue Selection Highlighting**: Changed selected moment cards to blue background with white text for better visual feedback
- **Progress Bar Improvement**: Added dedicated progress bar below the Process Video button with percentage display
- **Card Dimensions Optimization**: Made moment cards less wide and taller to better accommodate text content
- **Rounded UI Elements**: Added rounded corners to all buttons, cards, and UI elements for a modern look
- **Darker Backgrounds**: Improved readability with darker gray backgrounds for moment cards and file name labels
- **Consistent Button Sizing**: Standardized button sizes throughout the interface
- **Improved Status Display**: Enhanced status reporting during video processing
- **Tab Arrangement**: Placed transcript tab first for improved workflow

## Version 1.2.1 (March 20, 2025)

### Video UI Improvements
- **Fixed UI Layout Issues**: Increased window width to 1400px to prevent elements from being cut off on the right side
- **Added CREATE REELS Button**: Added a prominent green CREATE REELS button at the top of the interface for better visibility
- **Improved Reel Creation**: Implemented robust reel creation functionality with progress indication and error handling
- **Added Output Folder Access**: Added a "View Output Folder" button to easily access created video reels
- **Enhanced Threading**: Video processing now runs in a background thread to prevent UI freezing
- **Improved User Experience**: Better feedback during reel creation with progress dialog and success/error messages
- **Fixed Selection Controls**: Improved layout of selection controls (Select All/None buttons)

## Version 1.2.0 (March 20, 2025)

### Video Processing Improvements
- **Fixed MoviePy Integration**: Improved error handling and dependency management for the video processing module
- **Added Dependency Installation**: Added a button to install missing dependencies directly from the UI
- **Better Error Reporting**: Enhanced error messages to provide more detailed information about missing dependencies
- **Improved Fallback Behavior**: Better handling of cases where MoviePy is not available

### GUI Improvements
- **Fixed Qt Platform Plugin Issue**: Resolved the "Could not find the Qt platform plugin 'cocoa'" error by properly setting the QT_PLUGIN_PATH environment variable
- **Added Clickable Launcher**: Created an AI_Assistant.command file that can be double-clicked to launch the app from Finder
- **Diagnostic Tools**: Added diagnostic scripts to help identify and fix Qt-related issues
- **Improved Error Handling**: Better handling of Qt initialization errors with informative error messages

### Chat Library Improvements
- **Fixed Chat Loading**: Resolved issues with loading previous chat sessions from the library
- **Added Chat Deletion**: Implemented right-click context menu to delete chats and their associated context
- **Improved Chat Titles**: Enhanced chat title generation based on the first user message
- **Backward Compatibility**: Added support for both old and new chat file formats
- **Memory Management**: Fixed issues with the memory manager to properly handle chat loading and deletion
- **CLI Interface**: Added a command-line interface for managing chats when the GUI is unavailable

### Bug Fixes
- **App Hanging at 90%**: Fixed critical error in conversation_manager.py where it was calling a non-existent method `get_chat_context()` instead of the correct `get_memory_context()`
- **UI Improvements**: Fixed issues with button text being cut off and improved layout to accommodate the chat library sidebar
- **Error Handling**: Added better error handling for chat loading and deletion operations

## Version 1.1.0 (March 20, 2025)

### Video Processing Feature
- **Fixed Video Transcription**: Updated the video processing module to work with the latest version of moviepy
- **Improved Key Point Extraction**: Enhanced the algorithm to extract key points even from videos with limited speech content
- **API Compatibility**: Updated method calls to match the current moviepy API (version 1.0.3)
- **Text Overlay**: Fixed text caption rendering on video clips
- **Dependency Management**: Ensured all required dependencies are properly installed in the virtual environment

### UI Improvements
- **Enhanced Chat Bubbles**: Improved the visual appearance and reliability of chat bubbles
- **Fixed Message Spacing**: Added proper spacing between messages for better readability
- **Improved Calendar Display**: Added visual cards for calendar events and calendar lists
- **Better Error Handling**: Added more informative error messages when connections fail

### Calendar Integration
- **Calendar Listing**: Fixed functionality to properly display available calendars from macOS Calendar app
- **Calendar Selection**: Improved the ability to select specific calendars for adding events
- **Event Creation**: Enhanced event creation with better date/time parsing
- **Visual Feedback**: Added special formatting for calendar-related messages

### Conversation Improvements
- **Reduced Repetition**: Fixed issues where the assistant would repeat questions
- **Better Context Handling**: Improved the assistant's ability to maintain context in conversations
- **More Natural Responses**: Enhanced the system prompt to generate more concise and helpful responses
- **Improved Error Recovery**: Better handling of connection issues and error states

### Technical Improvements
- **Enhanced Debugging**: Added more debug logging for calendar operations
- **Improved Thread Management**: Better handling of background tasks for smoother UI experience
- **Memory Management**: Fixed issues with memory context handling
- **Error Handling**: More robust error handling throughout the application

## [Unreleased]
- Fixed video transcription and key point extraction issues
- Fixed compatibility with moviepy 1.0.3 by updating API calls
- Optimized key point extraction algorithm to create fewer, more meaningful reels
  - Added intelligent segment combining for related content
  - Improved selection criteria for meaningful segments
  - Added minimum duration requirements for clips
  - Limited maximum number of reels created
  - Enhanced speech density analysis for better segment selection

## Version 1.0.0 (Initial Release)

- Basic chat interface with PyQt6
- Integration with LLaMA 3.1 model for local inference
- Web search capabilities
- Memory system for context retention
- Initial calendar integration with macOS Calendar app
