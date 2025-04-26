"""
System message handlers for API routes.

This module contains handlers for system messages and related functionality.
"""

import logging
import json
import uuid
from datetime import datetime
from flask import request, g
from managers.user_session_manager import UserSessionManager
from models import SystemMessage
from .common import create_error_response, create_success_response

# Create logger
logger = logging.getLogger(__name__)

def handle_send_system_message(session_id=None):
    """Handler to send a system message"""
    try:
        user_id = g.user['user_id']
        data = request.get_json()
        
        # Validate request
        if not data or 'content' not in data or 'type' not in data:
            return create_error_response('Content and type are required for system messages')
        
        # Extract parameters
        content = data['content']
        message_type = data['type']
        session_id = session_id or data.get('session_id')
        
        # Get conversation manager if session_id provided
        if session_id:
            _, conversation_manager = UserSessionManager.get_conversation_manager_for_user_session(user_id, session_id)
            
            # Format system message content as a string
            system_message_content = json.dumps({
                "content": content,
                "type": message_type
            })
            
            # Send system message using process_user_message instead of add_system_message
            conversation_manager.contextual_memory.process_user_message(session_id, system_message_content)
            
            # Create a response structure similar to what add_system_message would return
            system_message = {
                'id': str(uuid.uuid4()),  # Generate a unique ID
                'content': content,
                'message_type': message_type,
                'created_at': datetime.now()
            }
            
            return create_success_response({
                'message': 'System message sent successfully',
                'system_message': {
                    'id': system_message['id'],
                    'content': system_message['content'],
                    'type': system_message['message_type'],
                    'created_at': system_message['created_at'].isoformat() if system_message['created_at'] else None,
                }
            })
        else:
            # Create global system message (not associated with a session)
            from managers.system_message_manager import SystemMessageManager
            system_message = SystemMessageManager.create_system_message(content, message_type, user_id)
            
            return create_success_response({
                'message': 'Global system message created successfully',
                'system_message': {
                    'id': system_message.id,
                    'content': system_message.content,
                    'type': system_message.message_type,
                    'created_at': system_message.created_at.isoformat() if system_message.created_at else None,
                }
            })
    except Exception as e:
        logger.error(f"Error sending system message: {str(e)}", exc_info=True)
        return create_error_response(f'Error sending system message: {str(e)}', 500)

def handle_get_system_messages(session_id):
    """Handler to get system messages for a session"""
    try:
        user_id = g.user['user_id']
        
        # Verify session belongs to user
        session = UserSessionManager.get_session_by_id(session_id, user_id)
        
        if not session:
            return create_error_response('Session not found or access denied', 404)
        
        # Get system messages for the session
        system_messages = UserSessionManager.get_system_messages_for_session(session_id)
        
        # Convert to serializable format
        message_list = []
        for msg in system_messages:
            message_list.append({
                'id': msg.id,
                'content': msg.content,
                'type': msg.message_type,
                'created_at': msg.created_at.isoformat() if msg.created_at else None,
            })
            
        return create_success_response({
            'system_messages': message_list,
            'session_id': session_id
        })
    except Exception as e:
        logger.error(f"Error retrieving system messages: {str(e)}", exc_info=True)
        return create_error_response(f'Error retrieving system messages: {str(e)}', 500)

def handle_get_system_message():
    """Handler to get a specific system message by type"""
    try:
        message_type = request.args.get('type', 'welcome')
        
        # Define common system messages
        system_messages = {
            'welcome': 'Welcome to RAI Chat! How can I help you today?',
            'help': 'You can ask me questions, chat with me, or use commands like [SEARCH: your query] to search for information.',
            'error': 'Sorry, there was an error processing your request.'
        }
        
        message = system_messages.get(message_type, system_messages['welcome'])
        
        return create_success_response({
            'content': message,
            'type': message_type,
            'id': f'sys_{message_type}'
        })
    except Exception as e:
        logger.error(f"Error getting system message: {str(e)}", exc_info=True)
        return create_error_response(f'Error getting system message: {str(e)}', 500)
