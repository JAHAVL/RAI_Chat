# RAI_Chat/backend/api/docker_chat.py
"""
-------------------------------------------------------------------------
FILE PURPOSE (FOR NON-DEVELOPERS):

This file ONLY defines the API endpoint (access point) for chat messages.
It does NOT implement the actual chat processing - it's where the application
receives chat messages and routes them to the appropriate services and managers.

Endpoints defined here:
- /chat - Accepts user messages and returns AI responses

This file supports both regular responses and streaming responses (where the
AI's answer appears word by word in real-time, like watching someone type).

Think of this file as the mail room that receives your letters but doesn't
actually write the responses - it just passes them to the right department.

This file was recently fixed to properly handle conversation management
by correctly unpacking session_id and conversation_manager objects.
-------------------------------------------------------------------------
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response

# Use absolute imports for Docker
from core.auth.docker_utils import token_required
from managers.docker_user_session_manager import UserSessionManager

logger = logging.getLogger(__name__)

# Create a blueprint for chat
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('', methods=['POST'])
@token_required
def chat():
    """
    Chat endpoint using conversation manager, supporting streaming.
    
    Expected request format:
    {
        "message": "User's message text",
        "session_id": "optional-session-id"  # If not provided, a new session will be created
    }
    
    Returns:
        A streaming response with chunks of the AI's response
    """
    try:
        # Get the request data
        data = request.get_json()
        
        # Validate required fields
        if 'message' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: message'
            }), 400
        
        # Extract data
        user_input = data.get('message')
        session_id = data.get('session_id')  # This might be None
        
        # Get the user ID from the authenticated user
        user_id = g.user.get('user_id') if hasattr(g, 'user') and g.user else 1
        
        # Log the incoming message
        logger.info(f"Received chat message from user {user_id}: {user_input[:50]}...")
        
        # Get the user session manager
        user_session_manager = UserSessionManager()
        
        # Get or create a conversation manager for this session
        conversation_manager = user_session_manager.get_conversation_manager(
            user_id=user_id,
            session_id=session_id
        )
        
        # If no session_id was provided, get the new one from the conversation manager
        actual_session_id = conversation_manager.session_id
        
        # Process the message and stream the response
        def generate_response():
            # First send a test chunk to verify the frontend can parse it
            initial_chunk = {
                'type': 'system', 
                'content': 'Processing your message...', 
                'session_id': actual_session_id
            }
            yield json.dumps(initial_chunk) + '\n'
            
            try:
                for response_chunk in conversation_manager.process_message(user_input, actual_session_id):
                    # Ensure response_chunk is serializable
                    if not isinstance(response_chunk, dict):
                        response_chunk = {
                            'type': 'system',
                            'content': str(response_chunk),
                            'session_id': actual_session_id
                        }
                    
                    # Always include session_id
                    if 'session_id' not in response_chunk:
                        response_chunk['session_id'] = actual_session_id
                        
                    # Log what we're sending for debugging
                    logger.debug(f"Sending chunk: {json.dumps(response_chunk)[:100]}...")
                    
                    # Yield properly formatted NDJSON
                    yield json.dumps(response_chunk) + '\n'
            except Exception as e:
                logger.error(f"Error generating response: {str(e)}")
                error_response = {
                    'type': 'error',
                    'status': 'error',
                    'content': f'Error generating response: {str(e)}',
                    'session_id': actual_session_id
                }
                yield json.dumps(error_response) + '\n'
        
        # Return a streaming response
        return Response(
            generate_response(),
            mimetype='application/x-ndjson'
        )
    
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing chat request: {str(e)}'
        }), 500
