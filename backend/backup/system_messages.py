"""
-------------------------------------------------------------------------
FILE PURPOSE:

This file defines the API endpoint for system messages related to chat operations.
It handles status updates, notifications, and other system-level communications
separate from the actual LLM responses.

Endpoints defined here:
- /system-messages - Accepts and returns system messages related to search status, etc.

This separation ensures clear distinction between system operational messages
and actual LLM-generated chat responses.
-------------------------------------------------------------------------
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response

# Use absolute imports instead of relative imports
import sys
import os

# Add the backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Now use absolute imports
from core.auth.utils import token_required
from services.session import get_user_session_manager

system_messages_bp = Blueprint('system_messages', __name__)
logger = logging.getLogger(__name__)

@system_messages_bp.route('', methods=['POST'])
@token_required
def system_message():
    """
    System messages endpoint for operational status updates.
    This endpoint is separate from the main chat endpoint to clearly
    distinguish between system operational messages and actual responses.
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({
                'error': 'Invalid request data',
                'status': 'error'
            }), 400
        
        # Get required fields
        action = data.get('action')
        session_id = data.get('session_id')
        
        if not action or not session_id:
            return jsonify({
                'error': 'Action and session_id are required',
                'status': 'error'
            }), 400
        
        # Get user ID from auth token
        user_id = g.user_id
        
        # Handle different types of system messages
        if action == 'get_search_status':
            # Get user session manager
            user_session_manager = get_user_session_manager(user_id)
            
            # Get conversation manager for this session
            actual_session_id, conversation_manager = user_session_manager.get_conversation_manager(user_id, session_id)
            
            if not conversation_manager:
                logger.error(f"Failed to get conversation manager for user {user_id}, session {session_id}")
                return jsonify({"error": "Failed to initialize conversation manager", "status": "error"}), 500
            
            # Get the current search status for this session
            search_status = conversation_manager.get_search_status(actual_session_id)
            
            return jsonify({
                "type": "system",
                "action": "web_search",
                "status": search_status.get("status", "unknown"),
                "id": search_status.get("id", f"search-{int(datetime.now().timestamp())}"),
                "content": search_status.get("content", "Search status update"),
                "timestamp": datetime.now().isoformat(),
                "messageType": search_status.get("messageType", "info")
            })
        
        # Handle other system message types here
        # ...
        
        # Default response for unhandled action types
        return jsonify({
            'error': f'Unhandled system message action: {action}',
            'status': 'error'
        }), 400
        
    except Exception as e:
        logger.error(f"Error in system_message endpoint: {e}")
        return jsonify({
            'error': f'Error processing system message: {str(e)}',
            'status': 'error'
        }), 500
