# utils/path_manager.py
import os
from pathlib import Path
from typing import Union, Optional
import logging # Added for potential error logging if needed

# Basic logging setup (optional, but good practice)
logger = logging.getLogger(__name__)

# --- Base Path Determination ---
try:
    # Assumes this file is in RAI_Chat/backend/utils directory relative to the project root
    # Adjust the number of .parent calls if the file location changes
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve() # Go up 4 levels: utils -> backend -> RAI_Chat -> Project Root
    logger.info(f"Project root determined as: {PROJECT_ROOT}")
except Exception as e:
    logger.error(f"Could not automatically determine project root: {e}", exc_info=True)
    # Fallback or raise error - For now, let's raise to make the issue obvious
    raise RuntimeError("Failed to determine project root directory.") from e

# --- Static Paths (Relative to Project Root or RAI_Chat) ---
# Directories directly under Project Root
LLM_ENGINE_DIR = PROJECT_ROOT / "llm_Engine"
MODULES_DIR = PROJECT_ROOT / "modules" # Corrected case
RAI_CHAT_DIR = PROJECT_ROOT / "RAI_Chat"

# Directories now *inside* RAI_Chat/backend
BACKEND_DIR = RAI_CHAT_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
LOGS_DIR = BACKEND_DIR / "logs"
CONFIG_FILE = BACKEND_DIR / "config.py" # Assuming config.py moved here
DOCS_DIR = BACKEND_DIR / "docs"
SCRIPTS_DIR = BACKEND_DIR / "scripts"
TESTS_DIR = BACKEND_DIR / "tests"
# Note: MODULES_DIR is now top-level, not under PROJECT_ROOT in the old way

# --- Dynamic Path Functions ---

def get_user_base_dir(user_id: Union[str, int]) -> Path:
    """Gets the base directory for a specific user's data."""
    if not user_id:
        raise ValueError("user_id cannot be empty or None")
    return DATA_DIR / str(user_id)

# Removed get_user_chats_dir as it's replaced by session-specific dirs

def get_user_session_dir(user_id: Union[str, int], session_id: str) -> Path:
    """Gets the directory for a specific session's data."""
    if not session_id:
        raise ValueError("session_id cannot be empty or None")
    # Basic validation for session_id format might be good here if needed
    if ".." in session_id or "/" in session_id or "\\" in session_id:
         raise ValueError(f"Invalid session_id format: {session_id}")
    return get_user_base_dir(user_id) / session_id

# Removed get_user_memory_dir as user-level memory is now in DB

def get_user_videos_dir(user_id: Union[str, int]) -> Path:
    """Gets the directory for a specific user's video files."""
    return get_user_base_dir(user_id) / "videos" # Added videos directory

def get_user_video_filepath(user_id: Union[str, int], video_filename: str) -> Path:
    """Gets the full path for a specific video file for a user."""
    if not video_filename:
        raise ValueError("video_filename cannot be empty or None")
    # Basic sanitization/validation for filename (prevent path traversal)
    safe_filename = Path(video_filename).name # Extract only the filename part
    if not safe_filename or safe_filename != video_filename:
         raise ValueError(f"Invalid video_filename format: {video_filename}")

    videos_dir = get_user_videos_dir(user_id)
    # Let the calling code handle directory creation if needed
    return videos_dir / safe_filename

def get_user_chat_filepath(user_id: Union[str, int], session_id: str) -> Path:
    """Gets the full path for a specific chat session's transcript file."""
    session_dir = get_user_session_dir(user_id, session_id)
    # Let the calling code handle directory creation if needed
    return session_dir / "transcript.json"

# Removed get_user_session_metadata_filepath as metadata is in DB

def get_user_session_context_filepath(user_id: Union[str, int], session_id: str) -> Path:
    """Gets the full path for a specific chat session's context file."""
    session_dir = get_user_session_dir(user_id, session_id)
    # Let the calling code handle directory creation if needed
    return session_dir / "context.json"

# --- Helper Functions (Optional) ---

def ensure_directory_exists(path: Path):
    """Creates a directory if it doesn't exist."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
    except OSError as e:
        logger.error(f"Failed to create directory {path}: {e}", exc_info=True)
        raise # Re-raise the exception

# --- Example Usage (for reference) ---
if __name__ == "__main__":
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Logs Directory: {LOGS_DIR}")
    # print(f"User 1 Chats Dir: {get_user_chats_dir(1)}") # Removed example
    print(f"User 'test' Session Dir: {get_user_session_dir('test', 'session_123')}")
    print(f"User 'test' Transcript File: {get_user_chat_filepath('test', 'session_123')}")
    # print(f"User 'test' Memory Dir: {get_user_memory_dir('test')}") # Removed example
    print(f"User 'test' Context File: {get_user_session_context_filepath('test', 'session_123')}")
    print(f"User 'test' Videos Dir: {get_user_videos_dir('test')}")
    print(f"User 'test' Video File: {get_user_video_filepath('test', 'my_video.mp4')}")
    # Example of ensuring a dir exists
    # test_dir = LOGS_DIR / "test_subdir"
    # ensure_directory_exists(test_dir)
    # print(f"Checked/Created: {test_dir}")