"""
RAI_Chat/Backend/managers/system_message_manager.py
System message manager for the RAI Chat application.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from models.connection import get_db
from models import SystemMessage

# Set up logging
logger = logging.getLogger(__name__)


class SystemMessageManager:
    """
    Manages system messages for the RAI Chat application.
    
    This class:
    1. Creates and retrieves system messages
    2. Handles global system messages not associated with a specific session
    """
    
    @staticmethod
    def create_system_message(content: str, message_type: str, user_id: str, session_id: Optional[str] = None) -> SystemMessage:
        """
        Create a new system message.
        
        Args:
            content: The content of the system message
            message_type: The type of system message (e.g., 'info', 'warning', 'error')
            user_id: The ID of the user associated with this message
            session_id: Optional session ID. If not provided, this is a global system message.
            
        Returns:
            The created SystemMessage object
        """
        from models.connection import get_db
        from models import SystemMessage
        
        # Generate a unique message ID
        message_id = str(uuid.uuid4())
        
        # Create the system message in the database
        with get_db() as db:
            # Create a new system message
            new_message = SystemMessage(
                id=message_id,
                content=content,
                message_type=message_type,
                user_id=user_id,
                session_id=session_id,
                created_at=datetime.utcnow()
            )
            
            # Add to database
            db.add(new_message)
            db.commit()
            
            # Create a copy to return after the session closes
            message_copy = SystemMessage(
                id=new_message.id,
                content=new_message.content,
                message_type=new_message.message_type,
                user_id=new_message.user_id,
                session_id=new_message.session_id,
                created_at=new_message.created_at
            )
        
        logger.info(f"Created system message: {message_id} of type {message_type}")
        return message_copy
    
    @staticmethod
    def get_global_system_messages(user_id: str, limit: int = 10) -> List[SystemMessage]:
        """
        Get all global system messages for a user.
        
        Args:
            user_id: The ID of the user
            limit: Maximum number of messages to return
            
        Returns:
            List of global SystemMessage objects
        """
        messages = []
        
        with get_db() as db:
            # Query system messages for this user with no session ID
            db_messages = db.query(SystemMessage).filter(
                SystemMessage.user_id == user_id,
                SystemMessage.session_id == None
            ).order_by(SystemMessage.created_at.desc()).limit(limit).all()
            
            # Make copies of all messages before the session closes
            for msg in db_messages:
                messages.append(msg)
        
        return messages
