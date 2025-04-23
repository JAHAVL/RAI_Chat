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

# Use absolute imports for Docker
from core.auth.docker_utils import token_required

logger = logging.getLogger(__name__)

# Create a blueprint for system messages
system_messages_bp = Blueprint('system_messages', __name__)

@system_messages_bp.route('', methods=['POST'])
@token_required
def system_message():
    """
    System messages endpoint for operational status updates.
    This endpoint is separate from the main chat endpoint to clearly
    distinguish between system operational messages and actual responses.
    
    Expected request format:
    {
        "session_id": "unique-session-id",
        "message_type": "search_status",  # or other system message types
        "content": {
            "status": "searching",  # or "complete", "error"
            "query": "search query text",  # if applicable
            "details": "Additional details"  # optional
        }
    }
    
    Returns:
        A JSON response with the system message ID and timestamp
    """
    try:
        # Get the request data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['session_id', 'message_type', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Extract data
        session_id = data.get('session_id')
        message_type = data.get('message_type')
        content = data.get('content')
        
        # Generate a unique message ID
        import uuid
        message_id = f"sys_{uuid.uuid4()}"
        
        # Create the system message
        system_message = {
            'id': message_id,
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': session_id,
            'message_type': message_type,
            'content': content
        }
        
        # In a production system, you might want to store this in a database
        # For now, we'll just return the message
        
        # Return the system message
        return jsonify({
            'status': 'success',
            'message': 'System message received',
            'system_message': system_message
        })
    
    except Exception as e:
        logger.error(f"Error processing system message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing system message: {str(e)}'
        }), 500
