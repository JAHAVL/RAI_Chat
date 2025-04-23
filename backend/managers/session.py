# RAI_Chat/Backend/managers/session.py
# Helper module for session management with Docker-compatible imports

import logging
from typing import Tuple, Optional

# Import the UserSessionManager class
from .user_session_manager import UserSessionManager
from .conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

# Create a singleton instance of UserSessionManager to be reused
_user_session_manager = None

def get_user_session_manager(user_id: str, session_id: Optional[str] = None) -> Tuple[str, ConversationManager]:
    """
    Get or create a conversation manager for the specified user and session.
    
    This function maintains a singleton instance of UserSessionManager to avoid
    creating multiple instances unnecessarily.
    
    Args:
        user_id: The ID of the user
        session_id: Optional session ID. If not provided, a new session will be created.
        
    Returns:
        Tuple containing the session_id and conversation_manager
    """
    global _user_session_manager
    
    # Create the UserSessionManager singleton if it doesn't exist
    if _user_session_manager is None:
        logger.info("Creating new UserSessionManager instance")
        _user_session_manager = UserSessionManager()
    
    # Get or create a conversation manager for this user and session
    session_id, conversation_manager = _user_session_manager.get_conversation_manager(
        user_id=user_id,
        session_id=session_id
    )
    
    return session_id, conversation_manager
