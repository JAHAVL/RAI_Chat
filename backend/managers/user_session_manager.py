# RAI_Chat/Backend/managers/user_session_manager.py
# Standard user session manager for the RAI Chat application

import logging
import time
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

# Import the manager classes we need to instantiate
from .chat_file_manager import ChatFileManager
from .memory.contextual_memory import ContextualMemoryManager
from .memory.episodic_memory import EpisodicMemoryManager
from .conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

# Define a base path for data storage - In Docker, we use /app/data
DEFAULT_BASE_DATA_PATH = Path("/app/data")

class UserSessionManager:
    """
    Manages user sessions and provides access to conversation managers.
    
    This class:
    1. Creates and retrieves conversation managers for users
    2. Handles session persistence and cleanup
    3. Acts as a factory for conversation-related managers
    """
    
    def __init__(self, base_data_path: Optional[Path] = None):
        """
        Initialize the user session manager.
        
        Args:
            base_data_path: Base path for storing session data
        """
        self.base_data_path = base_data_path or DEFAULT_BASE_DATA_PATH
        self.base_data_path.mkdir(parents=True, exist_ok=True)
        
        # Dictionary to store active conversation managers by user_id and session_id
        self._conversation_managers: Dict[Tuple[str, str], ConversationManager] = {}
        
        # Dictionary to store last activity time for each conversation manager
        self._last_activity: Dict[Tuple[str, str], float] = {}
        
        # Initialize shared managers
        self.file_manager = ChatFileManager()
        
        logger.info(f"UserSessionManager initialized with base path: {self.base_data_path}")
    
    def get_conversation_manager(self, user_id: str, session_id: Optional[str] = None) -> Tuple[str, ConversationManager]:
        """
        Get or create a conversation manager for the specified user and session.
        
        Args:
            user_id: The ID of the user
            session_id: The ID of the session (optional, will create a new one if not provided)
            
        Returns:
            A tuple of (session_id, conversation_manager) for the user's session
        """
        # If no session_id is provided, create a new one
        if not session_id:
            session_id = self.file_manager.create_new_session_id()
            logger.info(f"Created new session ID: {session_id} for user: {user_id}")
        
        # Create a key for the conversation manager
        key = (user_id, session_id)
        
        # Check if we already have a conversation manager for this session
        if key in self._conversation_managers:
            # Update the last activity time
            self._last_activity[key] = time.time()
            return session_id, self._conversation_managers[key]
        
        # Create a new conversation manager
        logger.info(f"Creating new conversation manager for user: {user_id}, session: {session_id}")
        
        # Create memory managers for this session in the correct order
        # First create the episodic memory manager (takes only user_id)
        episodic_memory = EpisodicMemoryManager(
            user_id=user_id
        )
        
        # Then create the contextual memory manager (needs user_id and episodic memory manager)
        contextual_memory = ContextualMemoryManager(
            user_id=user_id,
            episodic_memory_manager=episodic_memory
        )
        
        # Create the conversation manager
        conversation_manager = ConversationManager(
            user_id=user_id,
            session_id=session_id,
            file_manager=self.file_manager,
            contextual_memory=contextual_memory,
            episodic_memory=episodic_memory
        )
        
        # Store the conversation manager and update last activity
        self._conversation_managers[key] = conversation_manager
        self._last_activity[key] = time.time()
        
        # Return the tuple of session_id and conversation_manager
        return session_id, conversation_manager
    
    def cleanup_inactive_sessions(self, max_inactive_time: int = 3600) -> int:
        """
        Clean up inactive conversation managers.
        
        Args:
            max_inactive_time: Maximum inactive time in seconds before cleanup (default: 1 hour)
            
        Returns:
            Number of conversation managers cleaned up
        """
        current_time = time.time()
        keys_to_remove = []
        
        # Find inactive conversation managers
        for key, last_activity in self._last_activity.items():
            if current_time - last_activity > max_inactive_time:
                keys_to_remove.append(key)
        
        # Remove inactive conversation managers
        for key in keys_to_remove:
            self._conversation_managers.pop(key, None)
            self._last_activity.pop(key, None)
        
        if keys_to_remove:
            logger.info(f"Cleaned up {len(keys_to_remove)} inactive conversation managers")
        
        return len(keys_to_remove)
    
    def get_session_history(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Get the history for a specific session.
        
        Args:
            user_id: The ID of the user
            session_id: The ID of the session
            
        Returns:
            The session history as a dictionary
        """
        # Use the file manager to get the session history
        return self.file_manager.get_session_history(user_id, session_id)
    
    def list_sessions(self, user_id: str) -> Dict[str, Any]:
        """
        List all sessions for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            A dictionary containing session information
        """
        # Use the file manager to list sessions
        return self.file_manager.list_sessions(user_id)
    
    def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        Delete a session and all associated data.
        
        Args:
            user_id: The ID of the user
            session_id: The ID of the session
            
        Returns:
            True if the session was deleted, False otherwise
        """
        # Remove the conversation manager if it exists
        key = (user_id, session_id)
        if key in self._conversation_managers:
            self._conversation_managers.pop(key, None)
            self._last_activity.pop(key, None)
        
        # Use the file manager to delete the session
        return self.file_manager.delete_session(user_id, session_id)
