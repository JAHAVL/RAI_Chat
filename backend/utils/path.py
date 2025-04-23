"""
Path management utilities for the RAI Chat application.
Centralizes path handling and provides utilities for path operations.
"""
import os
import logging
from typing import Union, Optional, Dict, List
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Determine if we're in Docker or local environment
def is_docker():
    path = '/proc/self/cgroup'
    return os.path.exists('/.dockerenv') or os.path.exists(path) and any('docker' in line for line in open(path))

# Set base directories based on environment
if is_docker():
    # Docker environment
    PROJECT_ROOT = Path('/app')
else:
    # Local environment - use current directory or user home
    PROJECT_ROOT = Path(os.getcwd())
    # Alternatively: PROJECT_ROOT = Path(os.path.expanduser('~/.rai_chat'))

# Define derived directories
DATA_DIR = PROJECT_ROOT / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Define log directories with proper separation
LOGS_DIR = PROJECT_ROOT / 'logs'
BACKEND_LOGS_DIR = LOGS_DIR / 'backend'
FRONTEND_LOGS_DIR = LOGS_DIR / 'frontend'
LLM_ENGINE_LOGS_DIR = LOGS_DIR / 'llm_engine'
STARTUP_LOGS_DIR = LOGS_DIR / 'startup'

# Ensure all log directories exist
for log_dir in [LOGS_DIR, BACKEND_LOGS_DIR, FRONTEND_LOGS_DIR, LLM_ENGINE_LOGS_DIR, STARTUP_LOGS_DIR]:
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        logger.warning(f"Failed to create log directory {log_dir}: {e}")
        # Fall back to a directory we can write to
        if not is_docker():
            log_dir = Path(os.path.expanduser('~/.rai_chat/logs'))
            log_dir.mkdir(parents=True, exist_ok=True)

# Other data directories
SESSIONS_DIR = DATA_DIR / 'sessions'
UPLOADS_DIR = DATA_DIR / 'uploads'
VIDEOS_DIR = DATA_DIR / 'videos'

# Ensure all data directories exist
for data_dir in [SESSIONS_DIR, UPLOADS_DIR, VIDEOS_DIR]:
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        logger.warning(f"Failed to create data directory {data_dir}: {e}")

# --- Directory Structure Utilities ---

def get_user_base_dir(user_id: Union[str, int]) -> Path:
    """Gets the base directory for a specific user's data."""
    user_dir = SESSIONS_DIR / str(user_id)
    return user_dir

def get_user_session_dir(user_id: Union[str, int], session_id: str) -> Path:
    """Gets the directory for a specific session's data."""
    user_dir = get_user_base_dir(user_id)
    session_dir = user_dir / session_id
    return session_dir

def get_user_videos_dir(user_id: Union[str, int]) -> Path:
    """Gets the directory for a specific user's video files."""
    return VIDEOS_DIR / str(user_id)

def get_user_video_filepath(user_id: Union[str, int], video_filename: str) -> Path:
    """Gets the full path for a specific video file for a user."""
    videos_dir = get_user_videos_dir(user_id)
    # Ensure the filename is safe
    safe_filename = os.path.basename(video_filename)
    if not safe_filename:
        raise ValueError(f"Invalid video filename: {video_filename}")
    return videos_dir / safe_filename

def get_user_chat_filepath(user_id: Union[str, int], session_id: str) -> Path:
    """Gets the full path for a specific chat session's transcript file."""
    session_dir = get_user_session_dir(user_id, session_id)
    return session_dir / "transcript.json"

def get_user_session_context_filepath(user_id: Union[str, int], session_id: str) -> Path:
    """Gets the full path for a specific chat session's context file."""
    session_dir = get_user_session_dir(user_id, session_id)
    return session_dir / "context.json"

# --- Helper Functions ---

def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """Creates a directory if it doesn't exist and returns the path."""
    try:
        # Convert string to Path if needed
        if isinstance(path, str):
            path = Path(path)
        
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
        return path
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to create directory {path}: {e}", exc_info=True)
        raise  # Re-raise the exception

# Simple version for string paths
def ensure_directory_exists_str(path_str: str) -> str:
    """Creates a directory if it doesn't exist and returns the path string."""
    try:
        os.makedirs(path_str, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path_str}")
        return path_str
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to create directory {path_str}: {e}", exc_info=True)
        raise  # Re-raise the exception
