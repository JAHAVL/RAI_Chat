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

# Create a singleton instance of UserSessionManager to be reused
_user_session_manager = None

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
    
    @staticmethod
    def get_instance(base_data_path: Optional[Path] = None) -> 'UserSessionManager':
        """
        Get or create the singleton instance of UserSessionManager.
        
        Args:
            base_data_path: Optional base path for storing session data
            
        Returns:
            The singleton UserSessionManager instance
        """
        global _user_session_manager
        
        # Create the UserSessionManager singleton if it doesn't exist
        if _user_session_manager is None:
            logger.info("Creating new UserSessionManager singleton instance")
            _user_session_manager = UserSessionManager(base_data_path)
        
        return _user_session_manager
    
    @staticmethod
    def get_conversation_manager_for_user_session(user_id: str, session_id: Optional[str] = None) -> Tuple[str, ConversationManager]:
        """
        Get or create a conversation manager for the specified user and session.
        
        This static method provides easy access to conversation managers through
        the singleton UserSessionManager instance.
        
        Args:
            user_id: The ID of the user
            session_id: Optional session ID. If not provided, a new session will be created.
            
        Returns:
            Tuple containing the session_id and conversation_manager
        """
        # Get the singleton instance
        instance = UserSessionManager.get_instance()
        
        # Get or create a conversation manager for this user and session
        return instance.get_conversation_manager(user_id, session_id)
    
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
            file_manager=self.file_manager,
            contextual_memory=contextual_memory,
            episodic_memory=episodic_memory
        )
        
        # Load the session after creating the conversation manager
        conversation_manager.load_session(session_id)
        
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
        from models.connection import get_db
        
        # Get a database session and use the file manager to list sessions
        with get_db() as db:
            return self.file_manager.list_sessions(db, user_id)
    
    def delete_session(self, user_id: str, session_id: str) -> bool:
        """
        Delete a session and all associated data.
        
        Args:
            user_id: The ID of the user
            session_id: The ID of the session
            
        Returns:
            True if the session was deleted, False otherwise
        """
        from models.connection import get_db
        
        # Remove the conversation manager if it exists
        key = (user_id, session_id)
        if key in self._conversation_managers:
            self._conversation_managers.pop(key, None)
            self._last_activity.pop(key, None)
        
        # Use the file manager to delete the session
        with get_db() as db:
            return self.file_manager.delete_session(db, user_id, session_id)
    
    @staticmethod
    def get_sessions_for_user(user_id: str):
        """
        Static convenience method to get all sessions for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of sessions for the user
        """
        from models.connection import get_db
        from models import Session
        
        # Initialize empty list in case there are no sessions
        sessions = []
        
        # Use the database directly to query sessions for this user
        with get_db() as db:
            db_sessions = db.query(Session).filter(Session.user_id == user_id).all()
            # Make a copy of the sessions before the session closes
            for session in db_sessions:
                sessions.append(session)
        
        return sessions
    
    @staticmethod
    def get_session_by_id(session_id: str, user_id: str):
        """
        Static convenience method to get a specific session by ID.
        
        Args:
            session_id: The ID of the session
            user_id: The ID of the user
            
        Returns:
            Session object if found, None otherwise
        """
        from models.connection import get_db
        from models import Session
        
        with get_db() as db:
            session = db.query(Session).filter(
                Session.id == session_id,
                Session.user_id == user_id
            ).first()
            
            # If no session found, return None
            if not session:
                return None
                
            # Make a copy of the session before the database session closes
            # to avoid DetachedInstanceError
            session_copy = Session(
                id=session.id,
                user_id=session.user_id,
                title=session.title,
                created_at=session.created_at,
                updated_at=session.updated_at
            )
        
        return session_copy
    
    @staticmethod
    def get_messages_for_session(session_id: str):
        """
        Static convenience method to get all messages for a session.
        
        Args:
            session_id: The ID of the session
            
        Returns:
            List of messages for the session
        """
        from models.connection import get_db
        from models import Message
        
        messages = []
        
        with get_db() as db:
            db_messages = db.query(Message).filter(Message.session_id == session_id).all()
            
            # Make copies of all messages before the session closes
            for msg in db_messages:
                messages.append(msg)
        
        return messages
    
    @staticmethod
    def get_message_count_for_session(session_id: str):
        """
        Static convenience method to get the message count for a session.
        
        Args:
            session_id: The ID of the session
            
        Returns:
            Number of messages in the session
        """
        from models.connection import get_db
        from models import Message
        
        with get_db() as db:
            count = db.query(Message).filter(Message.session_id == session_id).count()
            
        return count
    
    @staticmethod
    def reset_session(session_id: str, user_id: str):
        """
        Static convenience method to reset a session.
        
        Args:
            session_id: The ID of the session
            user_id: The ID of the user
            
        Returns:
            True if the session was reset, False otherwise
        """
        from models.connection import get_db
        from models import Message, Session
        from sqlalchemy import delete
        
        try:
            with get_db() as db:
                # Verify the session belongs to the user
                session = db.query(Session).filter(
                    Session.id == session_id,
                    Session.user_id == user_id
                ).first()
                
                if not session:
                    return False
                
                # Delete all messages for this session
                db.execute(delete(Message).where(Message.session_id == session_id))
                db.commit()
                
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def create_session(user_id: str, title: str = ""):
        """
        Static convenience method to create a new session.
        
        Args:
            user_id: The ID of the user
            title: Optional title for the session
            
        Returns:
            The created Session object
        """
        from models.connection import get_db
        from models import Session
        import datetime
        import uuid
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        
        # Create the session in the database
        with get_db() as db:
            # Create a new session
            new_session = Session(
                id=session_id,
                user_id=user_id,
                title=title or f"Chat {session_id[:8]}",
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            
            # Add to database
            db.add(new_session)
            db.commit()
            
            # Create a copy to return after the session closes
            session_copy = Session(
                id=new_session.id,
                user_id=new_session.user_id,
                title=new_session.title,
                created_at=new_session.created_at,
                updated_at=new_session.updated_at
            )
        
        return session_copy
