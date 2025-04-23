# RAI_Chat/backend/api/system_message.py
"""
-------------------------------------------------------------------------
FILE PURPOSE (FOR NON-DEVELOPERS):

This file defines the API endpoints (access points) for system messages. 
It does NOT contain the actual implementation - it's just where the 
application receives requests about system messages and routes them 
to the appropriate service.

System messages are important notifications during chat interactions like:
- Error messages when something goes wrong
- Success confirmations

Think of this file as the receptionist who takes your request about system
messages and passes it to the appropriate department (service) to handle.
The real work happens in the SystemMessageService that this file calls.
-------------------------------------------------------------------------
"""

import logging
from flask import Blueprint, request, jsonify, g
from ..core.auth.utils import token_required
from ..core.database.session import get_db
from ..services.system_message import SystemMessageService
from ..schemas.system_message import SystemMessageCreateSchema, SystemMessageListSchema

system_message_bp = Blueprint('system_message', __name__)
logger = logging.getLogger(__name__)

@system_message_bp.route('/', methods=['GET'])
@token_required
def get_all_system_messages():
    """Get all system messages for the current user."""
    try:
        user_id = g.user_id
        db = get_db()
        
        # Get session ID from query parameters
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({
                "status": "error",
                "error": "Session ID is required"
            }), 400
        
        # Create system message service
        system_message_service = SystemMessageService(db)
        
        # Get system messages
        messages = system_message_service.get_system_messages(user_id, session_id)
        
        # Convert to schema
        response = SystemMessageListSchema(
            messages=[message.to_dict() for message in messages],
            session_id=session_id,
            status="success"
        )
        
        return jsonify(response.dict())
    except Exception as e:
        logger.error(f"Error getting system messages: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to get system messages",
            "message": str(e)
        }), 500

@system_message_bp.route('/<session_id>', methods=['GET'])
@token_required
def get_system_messages(session_id):
    """Get all system messages for a session."""
    try:
        user_id = g.user_id
        db = get_db()
        
        # Create system message service
        system_message_service = SystemMessageService(db)
        
        # Get system messages
        messages = system_message_service.get_system_messages(user_id, session_id)
        
        # Convert to schema
        response = SystemMessageListSchema(
            messages=[message.to_dict() for message in messages],
            session_id=session_id,
            status="success"
        )
        
        return jsonify(response.dict())
    except Exception as e:
        logger.error(f"Error getting system messages: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to get system messages",
            "message": str(e)
        }), 500

@system_message_bp.route('/', methods=['POST'])
@token_required
def create_system_message():
    """Create a new system message."""
    try:
        data = request.get_json()
        user_id = g.user_id
        db = get_db()
        
        # Validate input
        try:
            create_data = SystemMessageCreateSchema(**data)
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": "Invalid input data",
                "message": str(e)
            }), 400
        
        # Get session ID
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({
                "status": "error",
                "error": "Session ID is required"
            }), 400
        
        # Create system message service
        system_message_service = SystemMessageService(db)
        
        # Create system message
        message = system_message_service.create_system_message(
            user_id=user_id,
            session_id=session_id,
            content=create_data.content,
            message_type=create_data.type,
            related_message_id=create_data.related_message_id,
            meta_data=create_data.meta_data
        )
        
        # Return the created message
        return jsonify({
            "status": "success",
            "messages": [message.to_dict()],
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error creating system message: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to create system message",
            "message": str(e)
        }), 500

@system_message_bp.route('/<message_id>', methods=['DELETE'])
@token_required
def delete_system_message(message_id):
    """Delete a system message."""
    try:
        user_id = g.user_id
        db = get_db()
        
        # Create system message service
        system_message_service = SystemMessageService(db)
        
        # Delete system message
        system_message_service.delete_system_message(user_id, message_id)
        
        # Return success
        return jsonify({
            "status": "success",
            "message": "System message deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting system message: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to delete system message",
            "message": str(e)
        }), 500
