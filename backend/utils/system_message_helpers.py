"""
System Message Utility Functions

This module provides helper functions for handling system messages throughout the application.
It centralizes common operations to ensure consistent behavior.
"""

import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union

from models.system_message import SystemMessage
from models.connection import get_db

# Configure logging
logger = logging.getLogger(__name__)

def create_system_message(
    content: Union[str, Dict[str, Any]],
    message_type: str,
    session_id: str,
    status: str = 'active',
    message_id: Optional[str] = None
) -> Optional[SystemMessage]:
    """
    Create a new system message in the database.
    
    Args:
        content: Content of the system message (string or JSON-serializable dict)
        message_type: Type of system message (e.g., 'web_search', 'notification')
        session_id: ID of the session this message belongs to
        status: Initial status of the message (default: 'active')
        message_id: Optional custom message ID
        
    Returns:
        Created SystemMessage object or None if creation failed
    """
    try:
        # Convert content to JSON if it's not already a string
        if not isinstance(content, str):
            content = json.dumps(content)
            
        # Generate a unique ID if none provided
        if not message_id:
            message_id = f"sys_{message_type}_{str(uuid.uuid4())[:8]}"
            
        # Create and store the system message
        with get_db() as db:
            system_message = SystemMessage(
                id=message_id,
                content=content,
                message_type=message_type,
                session_id=session_id,
                status=status
            )
            db.add(system_message)
            db.commit()
            db.refresh(system_message)
            
            logger.info(f"Created system message: {message_id} of type {message_type} for session {session_id}")
            return system_message
            
    except Exception as e:
        logger.error(f"Error creating system message: {str(e)}")
        return None

def update_system_message(
    message_id: str,
    new_status: str,
    new_content: Optional[Union[str, Dict[str, Any]]] = None,
    session_id: Optional[str] = None
) -> Optional[SystemMessage]:
    """
    Update an existing system message.
    
    Args:
        message_id: ID of the message to update
        new_status: New status value (e.g., 'active', 'complete', 'error')
        new_content: Optional new content
        session_id: Optional session ID for verification
        
    Returns:
        Updated SystemMessage object or None if update failed
    """
    try:
        # Convert content to JSON if provided and not already a string
        if new_content is not None and not isinstance(new_content, str):
            new_content = json.dumps(new_content)
            
        with get_db() as db:
            # Build query
            query = db.query(SystemMessage).filter(SystemMessage.id == message_id)
            
            # Add session filter if provided
            if session_id:
                query = query.filter(SystemMessage.session_id == session_id)
                
            # Get the message
            system_message = query.first()
            
            if not system_message:
                logger.warning(f"System message {message_id} not found")
                return None
                
            # Update fields
            system_message.status = new_status
            if new_content is not None:
                system_message.content = new_content
                
            # Update timestamp (handled automatically by SQLAlchemy if using onupdate)
            db.commit()
            db.refresh(system_message)
            
            logger.info(f"Updated system message {message_id} to status: {new_status}")
            return system_message
            
    except Exception as e:
        logger.error(f"Error updating system message: {str(e)}")
        return None

def get_system_message(
    message_id: str,
    session_id: Optional[str] = None
) -> Optional[SystemMessage]:
    """
    Retrieve a system message by ID.
    
    Args:
        message_id: ID of the message to retrieve
        session_id: Optional session ID for filtering
        
    Returns:
        SystemMessage object or None if not found
    """
    try:
        with get_db() as db:
            # Build query
            query = db.query(SystemMessage).filter(SystemMessage.id == message_id)
            
            # Add session filter if provided
            if session_id:
                query = query.filter(SystemMessage.session_id == session_id)
                
            # Get the message
            system_message = query.first()
            
            if not system_message:
                logger.warning(f"System message {message_id} not found")
                
            return system_message
            
    except Exception as e:
        logger.error(f"Error retrieving system message: {str(e)}")
        return None

def get_system_messages_for_session(session_id: str) -> list:
    """
    Retrieve all system messages for a session.
    
    Args:
        session_id: ID of the session
        
    Returns:
        List of SystemMessage objects
    """
    try:
        with get_db() as db:
            messages = db.query(SystemMessage).filter(
                SystemMessage.session_id == session_id
            ).order_by(SystemMessage.timestamp.desc()).all()
            
            return messages
            
    except Exception as e:
        logger.error(f"Error retrieving system messages for session {session_id}: {str(e)}")
        return []

def format_system_message_for_api(system_message: SystemMessage) -> Dict[str, Any]:
    """
    Format a SystemMessage object for API responses.
    
    Args:
        system_message: SystemMessage object
        
    Returns:
        Dictionary with formatted system message data
    """
    if not system_message:
        return {}
        
    # Parse content if it's JSON
    content = system_message.content
    try:
        if isinstance(content, str):
            content = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        # If it's not valid JSON, keep as is
        pass
        
    return {
        'id': system_message.id,
        'type': 'system',
        'action': system_message.message_type,
        'status': system_message.status,
        'content': content,
        'timestamp': system_message.timestamp.isoformat() if system_message.timestamp else None,
        'updated_at': system_message.updated_at.isoformat() if hasattr(system_message, 'updated_at') and system_message.updated_at else None,
        'session_id': system_message.session_id
    }
