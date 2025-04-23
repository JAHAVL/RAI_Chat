# RAI_Chat/backend/api/session.py
"""
-------------------------------------------------------------------------
FILE PURPOSE (FOR NON-DEVELOPERS):

This file ONLY defines the API endpoints (access points) for chat sessions.
It does NOT implement the actual session management - it just receives
requests about sessions and routes them to the appropriate services.

Endpoints defined here:
- /sessions - Lists all of a user's chat sessions
- /sessions/{session_id} - Deletes a specific chat session
- /sessions/{session_id}/history - Gets message history from a session

Think of this file as the receptionist who takes requests about your past
conversations but passes the actual work to the filing department (services).

This file was recently fixed to properly handle the conversation manager
by correctly unpacking the tuple returned by get_conversation_manager().
-------------------------------------------------------------------------
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g

# Use absolute imports consistently for Docker environment
from core.auth.utils import token_required
from managers.session import get_user_session_manager
from core.database.session import get_db

session_bp = Blueprint('session', __name__)
logger = logging.getLogger(__name__)

@session_bp.route('/list', methods=['GET'])
@token_required
def list_sessions():
    """List saved sessions for the authenticated user"""
    try:
        # Get user ID from auth token
        user_id = g.user.get('user_id') if hasattr(g, 'user') and g.user else None
        
        if not user_id:
            logger.error("User ID not found in auth token")
            return jsonify({"error": "User ID not found"}), 401
        
        # Get the conversation manager
        _, conversation_manager = get_user_session_manager(user_id)
        
        # Check if we got a valid conversation manager
        if not conversation_manager:
            logger.error(f"Failed to get conversation manager for user {user_id}")
            return jsonify({"error": "Failed to initialize conversation manager"}), 500
        
        # Use the context manager properly with a 'with' statement
        from core.database.session import get_db
        sessions = []
        try:
            with get_db() as db:
                # List saved sessions using the file_manager
                sessions = conversation_manager.chat_file_manager.list_sessions(db, user_id)
        except Exception as e:
            logger.error(f"Database error when listing sessions: {e}")
            return jsonify({"error": "Database error"}), 500
        
        return jsonify({
            'sessions': sessions,
            'status': 'success'
        })
        
    except Exception as e:
        user_id = g.user.get('user_id') if hasattr(g, 'user') and g.user else 'unknown'
        logger.error(f"Error listing sessions for user {user_id}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to list sessions',
            'status': 'error'
        }), 500

@session_bp.route('/<session_id>', methods=['DELETE'])
@token_required
def delete_session(session_id):
    """Delete a specific saved session"""
    try:
        # Get user ID from auth token
        user_id = g.user.get('user_id') if hasattr(g, 'user') and g.user else None
        
        if not user_id:
            logger.error("User ID not found in auth token")
            return jsonify({"error": "User ID not found"}), 401
        
        # Get conversation manager
        _, conversation_manager = get_user_session_manager(user_id)
        
        # Use the context manager properly with a 'with' statement
        from core.database.session import get_db
        success = False
        try:
            with get_db() as db:
                # Delete the session using the chat_file_manager
                success = conversation_manager.chat_file_manager.delete_session(db, user_id, session_id)
        except Exception as e:
            logger.error(f"Database error when deleting session {session_id}: {e}")
            return jsonify({"error": "Database error"}), 500
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Session {session_id} deleted successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to delete session {session_id}'
            }), 404
            
    except Exception as e:
        user_id = g.user.get('user_id') if hasattr(g, 'user') and g.user else 'unknown'
        logger.error(f"Error deleting session {session_id} for user {user_id}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to delete session',
            'status': 'error'
        }), 500

@session_bp.route('/<session_id>/history', methods=['GET'])
@token_required
def get_session_history(session_id):
    """Get message history for a specific saved session"""
    try:
        # Get user ID from auth token
        user_id = g.user.get('user_id') if hasattr(g, 'user') and g.user else None
        
        if not user_id:
            logger.error("User ID not found in auth token")
            return jsonify({"error": "User ID not found"}), 401
        
        # Get conversation manager
        _, conversation_manager = get_user_session_manager(user_id)
        
        # Initialize empty history
        history = None
        try:
            # Use direct file method as this doesn't require DB connection
            history = conversation_manager.chat_file_manager.get_session_transcript(user_id, session_id)
        except Exception as e:
            logger.error(f"Error retrieving session history for {session_id}: {e}")
            return jsonify({"error": "Failed to retrieve session history"}), 500
        
        if history:
            return jsonify({
                'status': 'success',
                'history': history
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting history for session {session_id}: {e}")
        return jsonify({
            'error': 'Failed to get session history',
            'status': 'error'
        }), 500


@session_bp.route('/create', methods=['POST'])
@token_required
def create_session():
    """
    Create a new session explicitly with a title and optional initial message.
    
    Expected request format:
    {
        "title": "Session title",
        "message": "Optional initial message"
    }
    
    Returns:
        The session ID and status
    """
    try:
        # Get the request data
        data = request.get_json()
        
        # Validate required fields
        if 'title' not in data:
            return jsonify({
                'status': 'error', 
                'message': 'Missing required field: title'
            }), 400
            
        # Get user ID from auth token
        user_id = g.user.get('user_id')
        if not user_id:
            logger.error("User ID not found in auth token")
            return jsonify({"error": "User ID not found"}), 401
        
        # Get user session manager and conversation manager
        session_id, conversation_manager = get_user_session_manager(user_id)
        
        # Use the context manager properly with a 'with' statement
        try:
            with get_db() as db:
                # Create session metadata
                session_metadata = {
                    'title': data.get('title')
                }
                
                # Create an empty transcript or with initial message if provided
                transcript_data = []
                if 'message' in data:
                    transcript_data.append({
                        'role': 'user',
                        'content': data.get('message'),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                
                # Save the session transcript and metadata
                success = conversation_manager.chat_file_manager.save_session_transcript(
                    db, 
                    int(user_id), 
                    session_id, 
                    transcript_data, 
                    session_metadata
                )
                
                if success:
                    return jsonify({
                        'status': 'success',
                        'message': 'Session created successfully',
                        'session_id': session_id
                    })
                else:
                    logger.error(f"Failed to create session for user {user_id}")
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to create session'
                    }), 500
        except Exception as e:
            logger.error(f"Database error when creating session: {e}")
            return jsonify({"error": "Database error"}), 500
                
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error creating session: {str(e)}'
        }), 500
