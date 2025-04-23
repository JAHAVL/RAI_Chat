# AI Assistant App

A powerful desktop application that combines video processing, calendar management, and AI-powered chat capabilities with advanced contextual memory.

## Features

- Video processing with key point extraction and transcript summarization
- Calendar integration and event management
- AI chat interface with 3-tier contextual memory system
- Modern Electron/React-based user interface

## Requirements

- Python 3.11 or higher
- Node.js (for frontend development/building)
- FFmpeg (for video processing - ensure it's in your system's PATH)
- Ollama with a suitable model (e.g., llama3.1) running locally (default: http://localhost:11434)
- Required Python packages (install via pip):
  ```bash
  pip install -r requirements.txt
  ```
- Required Node packages (install via npm):
  ```bash
  cd RAI_Chat/frontend
  npm install
  cd ../..
  ```

## Important Notes

- **MoviePy:** The project uses `moviepy` (version specified in `requirements.txt`). Ensure FFmpeg is correctly installed and accessible in your system's PATH for MoviePy to function. Errors like `No module named 'moviepy.editor'` might indicate an incomplete MoviePy installation or issues finding FFmpeg.
- **Ollama:** Ensure Ollama is running and the desired model is available before starting the backend servers.

## Installation

1. Clone the repository
2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Install the specific MoviePy version:
   ```bash
   pip install moviepy==2.0.0.dev2
   ```
4. Make sure FFmpeg is installed on your system
5. Ensure Ollama is running with the llama3.1:latest model available

## Launching the App

The application uses a three-tier architecture with separate components that can be launched using a single unified script:

### 1. Unified Launch Script (Recommended)

The easiest way to launch all components together with proper process management:

```bash
# From the project root directory
python start_all.py
```

This script will:
- Automatically kill any existing instances of the LLM API Server, RAI API Server, and desktop application
- Launch the LLM API Server on port 6001
- Launch the RAI API Server on port 5001
- Start the frontend application on port 3000
- Launch the desktop app using the appropriate method for your environment
The script detects the appropriate method to launch the desktop application based on your project structure and environment.

**Note:** On first launch, you will be prompted to register a new user account before you can log in and use the application.


### 2. Launch Components Separately (For Development/Debugging)

For development purposes, you can also launch components individually for better error visibility:

1. **First, start the LLM API Server**:
   ```bash
   # From the project root directory
   PYTHONPATH=. LLM_API_PORT=6001 python -m llm_Engine.llm_api_server
   ```

2. **Next, start the RAI API Server**:
   ```bash
   # From the project root directory, in a new terminal
   PYTHONPATH=. RAI_API_PORT=5001 python -m RAI_Chat.rai_api_server
   ```

3. **Finally, start the Desktop Application**:
   ```bash
   # From the frontend directory, in a new terminal
   cd RAI_Chat/frontend && npm run electron:dev
   ```

This approach ensures each component logs to its own terminal window, making debugging easier.

### 3. Alternative Launch Methods

For backward compatibility, these methods are also supported but not recommended:

```bash
python launch_fixed.py  # Legacy launch script
```

Or for macOS users:

```bash
./AI_Assistant.command
```

## Component Architecture

The application consists of three main components:

1. **Frontend (Electron/React)**: The desktop user interface (port 3003)
2. **RAI API Server**: The main backend service that manages conversation, memory, and other features (port 5001)
3. **LLM API Server**: A separate service that handles communication with the Ollama LLM (port 6000)

This separation of concerns allows for better scalability and future migration to remote LLM services.

## Three-Tier Contextual Memory System

The AI Assistant uses a sophisticated three-tier memory system to maintain context across conversations while efficiently managing token usage:

### Memory Tiers

1. **Tier 1: Shorthand Context**
   - **Purpose**: Store critical information in a compact format
   - **Format**: Key-value pairs with shorthand notation
   - **Example**: `u/name=Jordan | u/preference=dark_mode`
   - **Token Efficiency**: Very high (minimal tokens)
   - **Persistence**: Stored indefinitely until explicitly removed
   - **Usage**: Always included in prompts for critical context

2. **Tier 2: Summarized Content**
   - **Purpose**: Provide condensed versions of conversation exchanges
   - **Format**: 1-2 sentence summaries of messages
   - **Example**: `User asked about project timeline. Assistant provided three milestone dates.`
   - **Token Efficiency**: High (moderate tokens)
   - **Persistence**: Maintained for the duration of the session
   - **Usage**: Included when detailed context is needed but full messages would be too token-heavy

3. **Tier 3: Raw Storage**
   - **Purpose**: Store complete, unaltered messages with metadata
   - **Format**: Full JSON objects with message content, role, timestamp, and other metadata
   - **Token Efficiency**: Low (high token count)
   - **Persistence**: Permanently stored until explicitly deleted
   - **Usage**: Used for reference and detailed context retrieval
   - **Frontend Display**: Only this tier is shown to the user in the chat interface

### Memory Flow

1. **Message Processing**:
   - When a user sends a message, it's stored in all three tiers.
   - The system automatically extracts important contextual information.
   - The assistant's response is also stored across all tiers.

2. **Response Generation**:
   - The system builds prompts including context from all three tiers.
   - Context is selected based on relevance to the current query.
   - The tiered approach ensures only necessary context is included to manage token count.

3. **Tier Selection Mechanism**:
   - The system dynamically determines which tier(s) to use based on:
     - Query complexity
     - Available token budget
     - Recency of information
     - Explicit user references to previous conversations

4. **Feedback Loop**:
   - As conversations continue, the system tracks which memory tiers were needed for each response.
   - This information helps optimize future context selection.
   - Messages that provided crucial context are prioritized in future retrievals.

### Technical Implementation

1. **Memory Storage**:
   - Contextual memory is stored in a JSON file (`contextual_memory.json`).
   - Each session maintains its own memory state.
   - Memory persists between application restarts.

2. **Response Formatting**:
   - The LLM API is instructed to generate responses in the three-tier format:
     ```json
     {
       "tier1": "Concise shorthand summary (max 20 words)",
       "tier2": "Brief 1-2 sentence summary for memory",
       "tier3": "Full detailed response shown to the user"
     }
     ```
   - The backend extracts the tier3 content to send to the frontend, while storing all tiers in memory.

3. **Context Retrieval**:
   - The memory manager implements intelligent retrieval algorithms to select the most relevant context.
   - Context is formatted specifically for inclusion in the system prompt.
   - The memory system tracks which contextual information was actually used in generating responses.

### Memory Management

1. **Session Management**:
   - Each user session has a unique session ID.
   - Memory is organized by session ID, allowing for multiple concurrent users.
   - Session isolation ensures privacy and context separation.

2. **Memory Persistence**:
   - The system automatically saves memory to disk after significant updates.
   - Memory can be loaded from disk when the system restarts.
   - Memory files can be backed up and restored.

3. **Memory Optimization**:
   - Older or less relevant memories may be downgraded from higher tiers to lower tiers.
   - The system tracks which memories were useful in generating responses.
   - Memory retrieval is optimized based on conversation patterns.

### Benefits of the Three-Tier Approach

1. **Token Efficiency**: Optimizes context inclusion based on available token budget.
2. **Context Retention**: Maintains critical information regardless of token constraints.
3. **Response Quality**: Ensures the LLM has necessary context for high-quality, consistent responses.
4. **User Experience**: Provides natural, context-aware conversations without unnecessary details.
5. **Scalability**: Allows for efficient handling of long-running conversations without losing context.

## Video Processing Features

The app includes comprehensive video processing capabilities:

1. **Video Transcription**: Uses Whisper model to transcribe video content
2. **Key Moments Extraction**: Identifies important moments in videos
3. **Transcript Summarization**: AI-powered summarization of video content with contextual memory integration
4. **Reel Creation**: Create highlight reels from selected key moments
5. **Interactive UI**: Card-style interface for displaying moments with proper text wrapping
6. **Video Metadata Tracking**: Stores and retrieves comprehensive metadata about videos, including:
   - Video length (calculated from key points timestamps)
   - Number of key points identified
   - Number of reels created

To use video features:
1. Click the "Video" tab in the application
2. Select a video file using the "Browse" button
3. Click "Process Video" to transcribe and analyze the video
4. Once processing is complete, you can ask the AI to summarize the video content by typing "summarize the video" or similar phrases
5. You can also ask specific questions about the video metadata, such as:
   - "How many key moments were identified in the video?"
   - "What's the length of the video?"
   - "How many reels were created from the video?"

## Video Memory System

The application uses a sophisticated approach to store and retrieve video information:

### Video Storage Process

1. **Initial Processing**:
   - When a video is processed, the `VideoProcessor` class extracts the transcript and key points
   - This information is passed to the `ContextualMemoryManager.process_video` method
   - The video information is stored in all three tiers of the contextual memory system

2. **Metadata Calculation and Storage**:
   - Video length is calculated from the timestamps in key points
   - Key points count is determined from the extracted key points
   - Reels count starts at 0 and is updated when reels are created
   - All metadata is stored in both Tier 1 (for quick access) and Tier 3 (for detailed storage)

3. **Reel Count Updates**:
   - When reels are created using the "Create Reels" button, the `VideoUI.on_reels_finished` method
   - This method calls `ContextualMemoryManager.update_video_metadata` to update the reels count
   - The update is applied to both Tier 1 and Tier 3 storage

### Video Retrieval Process

1. **Context Retrieval**:
   - When a user asks about a video, the `ConversationManager._is_video_related_query` method detects the query
   - The system then calls `ConversationManager._get_video_context` to retrieve the video context
   - This method first tries to get the context from the contextual memory system
   - If not found, it falls back to the legacy memory system

2. **Metadata Access**:
   - Video metadata is included in the context provided to the AI
   - The AI can access information about video length, key points count, and reels count
   - This information is formatted in a dedicated "VIDEO METADATA" section in the context

3. **Summary Generation**:
   - When a user asks for a video summary, the `ConversationManager.summarize_video` method is called
   - This method retrieves the video transcript, key points, and metadata
   - It includes the metadata in the prompt sent to the LLM
   - The generated summary includes the metadata at the beginning

### Memory Structure

Video information is stored in the contextual memory system as follows:

1. **Tier 1 (Shorthand Context)**:
   ```json
   "tier1": {
     "video": {
       "current_video": "video_filename.mp4",
       "video_length": 120.5,
       "key_points_count": 5,
       "reels_count": 2
     }
   }
   ```

2. **Tier 3 (Raw Storage)**:
   ```json
   {
     "role": "system",
     "content_type": "video",
     "video_path": "/path/to/video.mp4",
     "video_filename": "video_filename.mp4",
     "transcript": "Full transcript text...",
     "key_points": [
       {"start": 10.5, "end": 15.2, "text": "Key point 1"},
       {"start": 30.1, "end": 35.8, "text": "Key point 2"}
     ],
     "video_length": 120.5,
     "key_points_count": 5,
     "reels_count": 2,
     "session_id": "session_id",
     "timestamp": "2025-03-22T11:30:31"
   }
   ```

This comprehensive approach ensures that all video information is properly stored and can be retrieved when needed, providing users with detailed information about their videos.

## Expected Behavior

- The app should launch immediately with a GUI interface
- You'll see the main chat window and side panels
- Video processing and calendar features are accessible through the UI
- Progress indicators show status during video processing
- After video processing, a system message will appear in the chat indicating that the transcript is available

## Troubleshooting

If the app doesn't start:

1. Check that all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Verify FFmpeg installation:
   ```bash
   ffmpeg -version
   ```

3. Check the log files for errors:
   - `video_processing.log` for video-related issues
   - `conversation.log` for AI conversation issues

4. Verify Ollama is running:
   ```bash
   curl -s http://localhost:11434/api/version
   ```

5. If video features are not working, ensure you have the correct MoviePy version:
   ```bash
   pip install moviepy==2.0.0.dev2
   ```

## Development Status & Next Steps (March 31, 2025)

1.  **User Authentication (Complete):**
     *   **Backend:** Implemented user registration/login (SQLite, bcrypt, JWT), user-scoped managers, and protected API endpoints. See `RAI_Chat/auth_db.py`, `RAI_Chat/user_session_manager.py`, `RAI_Chat/rai_api_server.py`.
     *   **Frontend:** Implemented Login/Register UI (`RAI_Chat/frontend/src/components/auth/`), `AuthContext` for state management (`RAI_Chat/frontend/src/context/AuthContext.tsx`), updated API client (`RAI_Chat/frontend/src/api/rai_api.js`), and integrated the flow into `App.jsx`. Users are kept logged in via `localStorage`.
     *   **Status:** Backend and Frontend implementation is complete according to the plan documented in `docs/login_system_plan.md`.

2.  **Chat History Persistence (Fixed):**
    *   Resolved issues where chat history was not being saved or loaded correctly. This involved ensuring the `save_current_chat` method was called and that `load_chat` correctly used the `ChatFileManager`.

3.  **LLM API Server Instability (Known Issue):**
    *   **Symptom:** The LLM API server (`llm_api_server.py` run via `temp_run_llm_api.py`) frequently crashes with exit code -9 (SIGKILL) or -15 (SIGTERM).
    *   **Diagnosis:** Potential causes include excessive memory usage or Flask development server instability.
    *   **Attempted Fix:** Modified `start_all.py` to disable debug mode/reloader for the LLM server.
    *   **Status:** **Unresolved.** The LLM server instability persists and requires further investigation (memory profiling, WSGI server configuration).

4.  **Next Steps:**
     *   **LLM Server Stability:** Investigate and resolve the LLM API server crashes.
     *   **Testing:** Thoroughly test the end-to-end authentication flow and user data isolation.
     *   **Refinements:** Consider adding token refresh logic, more detailed user profile handling, and UI/UX improvements for authentication.


## Support

If you encounter any issues:
1. Check the logs in the application directory
2. Make sure all dependencies are correctly installed
3. Verify you're using Python 3.11 or higher

## Project Structure

The application follows a modern, modular architecture:

```
RAI_Chat/backend/
├── api/                # API endpoints
│   ├── auth.py         # Authentication endpoints
│   ├── chat.py         # Chat interaction endpoints
│   ├── memory.py       # Memory retrieval endpoints
│   └── session.py      # Session management endpoints
├── components/         # Reusable components
│   ├── action_handler.py  # Handles LLM response actions
│   ├── prompt_builder.py  # Constructs prompts for the LLM
│   └── prompts.py      # System prompt templates
├── core/               # Core application functionality
│   ├── database/       # Database models and connection
│   │   ├── connection.py  # Database connection management
│   │   └── models.py   # SQLAlchemy ORM models
│   └── auth/           # Authentication functionality
├── modules/            # Standalone functional modules
│   └── web_search/     # Web search functionality
├── schemas/            # Pydantic models for validation
│   ├── message.py      # Message schemas
│   ├── session.py      # Session schemas
│   ├── memory.py       # Memory schemas
│   └── user.py         # User schemas
├── services/           # Business logic services
│   ├── conversation.py  # Conversation management
│   ├── file_storage.py  # File storage management
│   ├── session.py      # User session management
│   └── memory/         # Memory management
│       ├── contextual.py  # Contextual memory management
│       └── episodic.py    # Episodic memory management
├── tests/              # Test suite
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── utils/              # Utility functions
│   └── path.py         # Path management utilities
├── app.py              # Application factory
├── config.py           # Configuration management
├── wsgi.py             # WSGI entry point
└── requirements.txt    # Project dependencies
```

## Test Suite

The project includes a comprehensive test suite organized by functionality:

```
tests/
├── api_tests/         # Tests for Ollama API integration
├── memory_tests/      # Tests for contextual memory system
├── video_tests/       # Tests for video processing functionality
├── integration_tests/ # Tests for multi-component features
├── run_tests.py       # Script to run tests by category
├── cleanup_tests.py   # Utility to clean up test files
└── README.md          # Detailed test documentation
```

### Running Tests

To run all tests:
```bash
cd tests
./run_tests.py all
```

To run tests for a specific category:
```bash
cd tests
./run_tests.py [category]  # where category is: api, memory, video, or integration
```

Refer to `tests/README.md` for detailed information about each test script.

## Dependencies

Core dependencies:
- PyQt6 - Modern UI framework
- moviepy - Video processing
- whisper - Audio transcription
- requests - HTTP client for web search
- python-dateutil - Date/time parsing

## Memory System

The application features a sophisticated 3-tier contextual memory system:

1. **Tier 1 (Shorthand Context)**: Stores critical information in key-value pairs with shorthand notation (e.g., `u/name=Jordan | u/dog_name=Max`). Used for user preferences, names, active tasks, and video metadata.

2. **Tier 2 (Summarized Content)**: Stores timestamped summaries of conversation exchanges with topic identification for quick reference. For videos, it includes a summary with key metadata and selected key points.

3. **Tier 3 (Raw Storage)**: Stores complete messages with metadata in individual JSON files for detailed reference when needed. For videos, it stores the complete transcript, all key points, and comprehensive metadata.

The system also includes:
- **Episodic Memory**: Retrieves relevant past conversations across different sessions
- **Video Context Integration**: Stores and retrieves video information in chat-specific storage, including metadata about video length, key points, and reels created

### Key Features
- Automatic extraction of user information, preferences, and tasks from messages
- Intelligent context retrieval based on query relevance
- System prompt integration to provide the LLM with necessary context
- Video transcript and metadata storage and retrieval within the contextual memory system
- Automatic updating of video metadata when reels are created

## Version Information

This is a stable version (20250322_stable) with fully functional:
- 3-tier contextual memory system
- Video processing and summarization
- Episodic memory retrieval
- Error handling and logging

Previous stable version: 20250321_stable
