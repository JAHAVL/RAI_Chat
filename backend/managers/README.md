# Managers Directory

This directory contains business logic managers for the RAI Chat application that handle application functionality beyond the database models.

## Directory Structure

- `__init__.py` - Initializes the managers package
- `user_session_manager.py` - Core manager for user sessions with singleton access pattern
- `conversation_manager.py` - Manages conversation state and messaging functionality
- `chat_file_manager.py` - Handles file operations for chat data
- `memory/` - Contains specialized memory management components

## The Manager Pattern

Managers in this application:
1. Encapsulate business logic and complex operations
2. Often work with multiple models from the database
3. Provide a higher-level API for the rest of the application
4. Handle caching and stateful operations

## Important Consideration: Models vs. Managers

- **Models (/models):** SQLAlchemy database models that define table structure 
- **Managers (this directory):** Business logic that operates on those models

## Video Transcript Retrieval

A key example of manager functionality is the video transcript retrieval system:

- When a video is selected in a chat session, a system message containing "Video selected:" is stored
- The memory management system prioritizes the video associated with the current chat session
- This ensures the system always uses the correct video transcript when generating summaries
- Prevents confusion when multiple videos exist in memory

## Usage Example

```python
# Get the singleton manager and a conversation manager for a specific user/session
from managers.user_session_manager import UserSessionManager

# Using the static method for convenience
session_id, conversation = UserSessionManager.get_conversation_manager_for_user_session(
    user_id="123", 
    session_id=None  # Creates a new session if None
)

# Now use the conversation manager for chat operations
response = conversation.process_message("Tell me about the video")
```
