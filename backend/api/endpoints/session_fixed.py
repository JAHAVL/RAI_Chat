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
import logging
from flask import Blueprint, request, jsonify, g
from core.auth.utils import token_required
from managers.session import get_user_session_manager

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
        
        # Get database session
        from ..core.database.session import get_db
        db = get_db()
        
        # Get user session manager
        user_session_manager = get_user_session_manager(user_id)
        
        # Get conversation manager - properly unpack the tuple (session_id, conversation_manager)
        _, conversation_manager = user_session_manager.get_conversation_manager(user_id)
        
        # Check if we got a valid conversation manager
        if not conversation_manager:
            logger.error(f"Failed to get conversation manager for user {user_id}")
            return jsonify({"error": "Failed to initialize conversation manager"}), 500
            
        # List saved sessions
        sessions = conversation_manager.list_saved_sessions(db)
        
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
        
        # Get user session manager
        user_session_manager = get_user_session_manager(user_id)
        
        # Delete the session
        success = user_session_manager.delete_session(user_id, session_id)
        
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
        
        # Get user session manager
        user_session_manager = get_user_session_manager(user_id)
        
        # Get the session history
        history = user_session_manager.get_session_history(user_id, session_id)
        
        if history:
            return jsonify({
                'status': 'success',
                'history': history
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Session {session_id} not found'
            }), 404
            
    except Exception as e:
        user_id = g.user.get('user_id') if hasattr(g, 'user') and g.user else 'unknown'
        logger.error(f"Error getting history for session {session_id} for user {user_id}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to get session history',
            'status': 'error'
        }), 500
