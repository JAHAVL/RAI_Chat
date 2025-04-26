"""
Session handlers for API routes.

This module contains handlers for session management and chat history.
"""

import logging
from flask import request, g
from managers.user_session_manager import UserSessionManager
from models import Session
from .common import create_error_response, create_success_response

# Create logger
logger = logging.getLogger(__name__)

def handle_get_sessions():
    """Handler to get all sessions for current user"""
    try:
        user_id = g.user['user_id']
        
        # Get sessions for the user
        sessions = UserSessionManager.get_sessions_for_user(user_id)
        
        # Convert to serializable format
        session_list = []
        for session in sessions:
            session_list.append({
                'id': session.id,
                'title': session.title or f"Chat {session.id[:8]}",
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'message_count': UserSessionManager.get_message_count_for_session(session.id)
            })
            
        return create_success_response({
            'sessions': session_list,
            'success': True
        })
    except Exception as e:
        logger.error(f"Error retrieving sessions: {str(e)}", exc_info=True)
        return create_error_response(f'Error retrieving sessions: {str(e)}', 500)

def handle_get_session(session_id):
    """Handler to get a specific session by ID"""
    try:
        user_id = g.user['user_id']
        
        # Verify session belongs to user
        session = UserSessionManager.get_session_by_id(session_id, user_id)
        
        if not session:
            return create_error_response('Session not found or access denied', 404)
        
        # Return session details
        return create_success_response({
            'session': {
                'id': session.id,
                'title': session.title or f"Chat {session.id[:8]}",
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'message_count': UserSessionManager.get_message_count_for_session(session.id)
            }
        })
    except Exception as e:
        logger.error(f"Error retrieving session: {str(e)}", exc_info=True)
        return create_error_response(f'Error retrieving session: {str(e)}', 500)

def handle_create_session():
    """Handler to create a new session"""
    try:
        user_id = g.user['user_id']
        data = request.get_json() or {}
        
        # Get optional title
        title = data.get('title', '')
        
        # Create new session
        session = UserSessionManager.create_session(user_id, title)
        
        return create_success_response({
            'session': {
                'id': session.id,
                'title': session.title or f"Chat {session.id[:8]}",
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None
            },
            'message': 'Session created successfully'
        })
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        return create_error_response(f'Error creating session: {str(e)}', 500)

def handle_delete_session(session_id):
    """Handler to delete a session"""
    try:
        user_id = g.user['user_id']
        
        # Delete the session
        success = UserSessionManager.delete_session(session_id, user_id)
        
        if not success:
            return create_error_response('Session not found or access denied', 404)
        
        return create_success_response({
            'message': 'Session deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}", exc_info=True)
        return create_error_response(f'Error deleting session: {str(e)}', 500)

def handle_get_chat_history(session_id):
    """Handler to get chat history for a session"""
    try:
        user_id = g.user['user_id']
        
        # Verify session belongs to user
        session = UserSessionManager.get_session_by_id(session_id, user_id)
        
        if not session:
            return create_error_response('Session not found or access denied', 404)
        
        # Get messages for the session
        messages = UserSessionManager.get_messages_for_session(session_id)
        
        # Convert to serializable format
        message_list = []
        for msg in messages:
            message_list.append({
                'id': msg.id,
                'content': msg.content,
                'role': msg.role,
                'created_at': msg.created_at.isoformat() if msg.created_at else None,
                'metadata': msg.metadata
            })
            
        return create_success_response({
            'messages': message_list,
            'session_id': session_id
        })
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}", exc_info=True)
        return create_error_response(f'Error retrieving chat history: {str(e)}', 500)

def handle_reset_session():
    """Handler to reset a session"""
    try:
        user_id = g.user['user_id']
        data = request.get_json()
        
        if not data or 'session_id' not in data:
            return create_error_response('Session ID is required')
        
        session_id = data['session_id']
        
        # Reset the session
        success = UserSessionManager.reset_session(session_id, user_id)
        
        if not success:
            return create_error_response('Session not found or access denied', 404)
        
        return create_success_response({
            'message': 'Session reset successfully',
            'session_id': session_id
        })
    except Exception as e:
        logger.error(f"Error resetting session: {str(e)}", exc_info=True)
        return create_error_response(f'Error resetting session: {str(e)}', 500)
