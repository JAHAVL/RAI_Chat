"""
pathconfig.py - Centralized path configuration for RAI Chat application

This module defines all paths used throughout the application in a single place,
making it easier to manage paths and ensure consistency across the codebase.

This is the main path utility file that consolidates functionality previously
found in path.py and path_manager.py.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Union, Optional, Dict, List

# Set up logging
logger = logging.getLogger(__name__)

# ----- ENVIRONMENT DETECTION -----

def is_docker() -> bool:
    """
    Determine if the code is running in a Docker container.
    
    Returns:
        bool: True if running in Docker, False otherwise
    """
    path = '/proc/self/cgroup'
    return os.path.exists('/.dockerenv') or os.path.exists(path) and any('docker' in line for line in open(path))

# ----- BASE DIRECTORIES -----

# Root directory determination based on environment
try:
    if is_docker():
        # Docker environment
        PROJECT_ROOT = Path('/app')
        BACKEND_DIR = PROJECT_ROOT
    else:
        # Local environment
        # Assumes this file is in backend/utils directory
        BACKEND_DIR = Path(__file__).parent.parent.resolve()
        PROJECT_ROOT = BACKEND_DIR.parent.parent  # Up two levels: utils -> backend -> RAI_Chat -> Project Root
        RAI_CHAT_DIR = BACKEND_DIR.parent  # The RAI_Chat directory containing backend and frontend
    
    # Log the detected paths at debug level
    logger.debug(f"Detected paths - PROJECT_ROOT: {PROJECT_ROOT}")
    logger.debug(f"Detected paths - BACKEND_DIR: {BACKEND_DIR}")
    if not is_docker():
        logger.debug(f"Detected paths - RAI_CHAT_DIR: {RAI_CHAT_DIR}")
except Exception as e:
    logger.error(f"Failed to determine base directories: {e}", exc_info=True)
    raise RuntimeError("Failed to initialize path configuration") from e

# ----- APPLICATION DIRECTORIES -----

# Backend directories
API_DIR = BACKEND_DIR / "api"
DATA_DIR = BACKEND_DIR / "data"
LOGS_DIR = BACKEND_DIR / "logs"
CONFIG_DIR = BACKEND_DIR / "config"
MODULES_DIR = BACKEND_DIR / "modules"
COMPONENTS_DIR = BACKEND_DIR / "components"
MANAGERS_DIR = BACKEND_DIR / "managers"
CORE_DIR = BACKEND_DIR / "core"
SCHEMAS_DIR = BACKEND_DIR / "schemas"
SERVICES_DIR = BACKEND_DIR / "services"
UTILS_DIR = BACKEND_DIR / "utils"
TESTS_DIR = BACKEND_DIR / "tests"
DOCS_DIR = BACKEND_DIR / "docs"
EXTENSIONS_DIR = BACKEND_DIR / "extensions"

# Define log directories with proper separation
BACKEND_LOGS_DIR = LOGS_DIR / 'backend'
if not is_docker():
    FRONTEND_LOGS_DIR = LOGS_DIR / 'frontend'
    LLM_ENGINE_LOGS_DIR = LOGS_DIR / 'llm_engine'
    STARTUP_LOGS_DIR = LOGS_DIR / 'startup'

# Data subdirectories
SESSIONS_DIR = DATA_DIR / 'sessions'
UPLOADS_DIR = DATA_DIR / 'uploads'
VIDEOS_DIR = DATA_DIR / 'videos'

# Frontend directories (in non-docker environments)
if not is_docker():
    FRONTEND_DIR = RAI_CHAT_DIR / "frontend"
    FRONTEND_SRC_DIR = FRONTEND_DIR / "src"
    FRONTEND_PUBLIC_DIR = FRONTEND_DIR / "public"
    FRONTEND_BUILD_DIR = FRONTEND_DIR / "build"

    # LLM Engine directories
    LLM_ENGINE_DIR = PROJECT_ROOT / "llm_Engine"  # Maintains original casing

# ----- FILE PATHS -----

# Config files
CONFIG_FILE = BACKEND_DIR / "config.py"
ENV_FILE = BACKEND_DIR / ".env"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
REQUIREMENTS_FILE = BACKEND_DIR / "requirements.txt"
DOCKER_REQUIREMENTS_FILE = BACKEND_DIR / "requirements.docker.txt"

# Database files
MAIN_DB_FILE = DATA_DIR / "rai_chat.db"
FALLBACK_DB_FILE = BACKEND_DIR / "rai_chat_fallback.db"

# ----- API PATHS -----

# API endpoint directory structure
API_ENDPOINTS_DIR = API_DIR / "endpoints"
API_EXTERNAL_DIR = API_DIR / "external"
API_LLM_ENGINE_DIR = API_DIR / "llm_engine"

# Main handler files
FRONTEND_API_HANDLER = API_DIR / "frontend_api_handler.py"
LLM_API_INTERFACE = API_LLM_ENGINE_DIR / "llm_api_interface.py"

# ----- UTILITY FUNCTIONS -----

def add_to_python_path(directory: Path) -> bool:
    """
    Add a directory to the Python path if it's not already there.
    This is useful for importing modules from non-standard locations.
    
    Args:
        directory (Path): The directory path to add to sys.path
        
    Returns:
        bool: True if the directory was added, False if it was already in the path
    """
    directory_str = str(directory)
    if directory_str not in sys.path:
        sys.path.append(directory_str)
        logger.debug(f"Added {directory_str} to Python path")
        return True
    return False

def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Make sure a directory exists, creating it and its parents if needed.
    
    Args:
        directory (Union[str, Path]): The directory path to check/create
        
    Returns:
        Path: The Path object for the directory
        
    Raises:
        OSError: If there's an error creating the directory
    """
    try:
        # Convert string to Path if needed
        if isinstance(directory, str):
            directory = Path(directory)
            
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")
        return directory
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to create directory {directory}: {e}", exc_info=True)
        raise  # Re-raise the exception

def get_user_base_dir(user_id: Union[str, int]) -> Path:
    """
    Gets the base directory for a specific user's data.
    
    Args:
        user_id (Union[str, int]): The user ID
        
    Returns:
        Path: The path to the user's base directory
        
    Raises:
        ValueError: If user_id is empty or None
    """
    if not user_id:
        raise ValueError("user_id cannot be empty or None")
    return DATA_DIR / str(user_id)

def get_user_session_dir(user_id: Union[str, int], session_id: str) -> Path:
    """
    Gets the directory for a specific session's data.
    
    Args:
        user_id (Union[str, int]): The user ID
        session_id (str): The session ID
        
    Returns:
        Path: The path to the session directory
        
    Raises:
        ValueError: If session_id is empty, None, or contains invalid characters
    """
    if not session_id:
        raise ValueError("session_id cannot be empty or None")
    
    # Basic validation for session_id format
    if ".." in session_id or "/" in session_id or "\\" in session_id:
        raise ValueError(f"Invalid session_id format: {session_id}")
        
    return get_user_base_dir(user_id) / session_id

def get_user_videos_dir(user_id: Union[str, int]) -> Path:
    """
    Gets the directory for a specific user's video files.
    
    Args:
        user_id (Union[str, int]): The user ID
        
    Returns:
        Path: The path to the user's videos directory
    """
    return VIDEOS_DIR / str(user_id)

def get_user_video_filepath(user_id: Union[str, int], video_filename: str) -> Path:
    """
    Gets the full path for a specific video file for a user.
    
    Args:
        user_id (Union[str, int]): The user ID
        video_filename (str): The video filename
        
    Returns:
        Path: The path to the video file
        
    Raises:
        ValueError: If video_filename is empty, None, or contains invalid characters
    """
    if not video_filename:
        raise ValueError("video_filename cannot be empty or None")
    
    # Basic sanitization/validation for filename (prevent path traversal)
    safe_filename = Path(video_filename).name  # Extract only the filename part
    if not safe_filename or safe_filename != video_filename:
        raise ValueError(f"Invalid video_filename format: {video_filename}")

    videos_dir = get_user_videos_dir(user_id)
    return videos_dir / safe_filename

def get_user_video_transcript_filepath(user_id: Union[str, int], video_filename: str) -> Path:
    """
    Gets the full path for a specific video's transcript file.
    
    Args:
        user_id (Union[str, int]): The user ID
        video_filename (str): The video filename (without the .transcript extension)
        
    Returns:
        Path: The path to the video transcript file
        
    Raises:
        ValueError: If video_filename is empty, None, or contains invalid characters
    """
    if not video_filename:
        raise ValueError("video_filename cannot be empty or None")
    
    # Basic sanitization/validation for filename
    safe_filename = Path(video_filename).stem  # Extract only the filename part without extension
    if not safe_filename:
        raise ValueError(f"Invalid video_filename format: {video_filename}")

    videos_dir = get_user_videos_dir(user_id)
    return videos_dir / f"{safe_filename}.transcript"

def get_video_metadata_filepath(user_id: Union[str, int], video_filename: str) -> Path:
    """
    Gets the full path for a video's metadata file.
    
    Args:
        user_id (Union[str, int]): The user ID
        video_filename (str): The video filename
        
    Returns:
        Path: The path to the video metadata file
    """
    if not video_filename:
        raise ValueError("video_filename cannot be empty or None")
    
    safe_filename = Path(video_filename).stem
    videos_dir = get_user_videos_dir(user_id)
    return videos_dir / f"{safe_filename}.metadata.json"

def get_user_chat_filepath(user_id: Union[str, int], session_id: str) -> Path:
    """
    Gets the full path for a specific chat session's transcript file.
    
    Args:
        user_id (Union[str, int]): The user ID
        session_id (str): The session ID
        
    Returns:
        Path: The path to the chat transcript file
    """
    session_dir = get_user_session_dir(user_id, session_id)
    return session_dir / "transcript.json"

def get_user_session_context_filepath(user_id: Union[str, int], session_id: str) -> Path:
    """
    Gets the full path for a specific chat session's context file.
    
    Args:
        user_id (Union[str, int]): The user ID
        session_id (str): The session ID
        
    Returns:
        Path: The path to the session context file
    """
    session_dir = get_user_session_dir(user_id, session_id)
    return session_dir / "context.json"

# ----- INITIALIZATION -----

# Ensure critical directories exist
for directory in [DATA_DIR, LOGS_DIR, SESSIONS_DIR, UPLOADS_DIR, VIDEOS_DIR]:
    try:
        ensure_directory_exists(directory)
    except (OSError, PermissionError) as e:
        logger.warning(f"Failed to create directory {directory}: {e}")

# Add backend directory to Python path for easier imports
add_to_python_path(BACKEND_DIR)

# Example for testing this module directly
if __name__ == "__main__":
    # Set up console logging for testing
    logging.basicConfig(level=logging.DEBUG)
    
    # Print out the configured paths
    print(f"Running in Docker: {is_docker()}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"BACKEND_DIR: {BACKEND_DIR}")
    print(f"API_DIR: {API_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    
    # Test utility functions
    test_dir = LOGS_DIR / "test_pathconfig"
    created = ensure_directory_exists(test_dir)
    print(f"Created test directory: {created}")
    
    # Test user-specific paths
    user_id = "test_user"
    session_id = "test_session"
    print(f"User base dir: {get_user_base_dir(user_id)}")
    print(f"User session dir: {get_user_session_dir(user_id, session_id)}")
    print(f"User chat file: {get_user_chat_filepath(user_id, session_id)}")
