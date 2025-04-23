# RAI_Chat/backend/api/chat.py
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
import re
from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response

# Use absolute imports consistently for Docker environment
from core.auth.utils import token_required
from managers.session import get_user_session_manager
from components.action_handler import perform_search

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

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
        # Get user and request data
        user_id = g.user['user_id']
        username = g.user['username']
        data = request.get_json()
        
        # Extract message and session info
        if not data or 'message' not in data:
            return jsonify({'status': 'error', 'message': 'No message provided'}), 400
        
        user_input = data['message']
        session_id = data.get('session_id')
        
        # --- DIRECT WEB SEARCH HANDLING ---
        # If the message contains a [SEARCH:] directive, handle it directly here
        search_match = re.search(r"\[SEARCH:\s*(.+?)\s*\]", user_input)
        if search_match:
            query = search_match.group(1).strip()
            logger.info(f"Direct web search requested via chat endpoint: {query}")
            
            # Start with an empty chunk to establish the connection
            def generate_search_response():
                # First send connection established
                yield '{"type":"connection_established"}\n'
                
                # Send system message that search is starting
                search_starting = {
                    'type': 'system',
                    'action': 'web_search',
                    'status': 'active',
                    'content': f"Searching the web for: {query}",
                    'timestamp': datetime.now().isoformat(),
                    'session_id': session_id
                }
                yield json.dumps(search_starting) + '\n'
                
                # Perform the search
                try:
                    # Directly use the perform_search function
                    search_results = perform_search(query=query)
                    
                    # Send the results
                    search_complete = {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'complete',
                        'content': search_results,
                        'timestamp': datetime.now().isoformat(),
                        'session_id': session_id
                    }
                    yield json.dumps(search_complete) + '\n'
                    
                    # Send a final content chunk with the search results
                    final_chunk = {
                        'type': 'content',
                        'content': search_results,
                        'timestamp': datetime.now().isoformat(),
                        'session_id': session_id
                    }
                    yield json.dumps(final_chunk) + '\n'
                    
                except Exception as e:
                    logger.error(f"Error performing direct web search: {e}")
                    error_chunk = {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'error',
                        'content': f"Error performing web search: {str(e)}",
                        'timestamp': datetime.now().isoformat(),
                        'session_id': session_id
                    }
                    yield json.dumps(error_chunk) + '\n'
            
            # Return the streaming response
            return Response(
                generate_search_response(),
                mimetype='application/x-ndjson'
            )
        
        # Get the user session manager and conversation manager
        session_id, conversation_manager = get_user_session_manager(user_id, session_id)
        
        # The session_id is already set in the conversation_manager by get_user_session_manager
        # We access the session ID from the conversation_manager directly
        session_id = conversation_manager.current_session_id
        
        # Note: The conversation manager already handles session loading and creation internally
        # No need to explicitly call load_chat or start_new_chat methods
        
        # Import requests to send system messages
        import requests
        import os
        
        # Function to send system messages via the dedicated API
        def send_system_message(session_id, message_type, content):
            try:
                # Get base URL from environment or use default
                api_base_url = os.environ.get('API_BASE_URL', 'http://localhost:6102')
                system_messages_url = f"{api_base_url}/api/system-messages"
                
                # Format payload for the system messages API
                payload = {
                    "session_id": session_id,
                    "message_type": message_type,
                    "content": content if isinstance(content, dict) else {"message": content}
                }
                
                # Send the request
                response = requests.post(system_messages_url, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"Failed to send system message: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error sending system message: {str(e)}")
        
        # Process the message and stream the response
        def generate_response():
            # Send initial processing message via system messages API
            send_system_message(
                session_id=session_id,
                message_type="status_update",
                content={
                    "status": "processing",
                    "message": "Processing your message...",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Start with an empty first chunk to establish the connection
            # This is important for streaming to begin but doesn't display anything
            yield '{"type":"connection_established"}\n'
            
            try:
                for response_chunk in conversation_manager.process_message(user_input, session_id):
                    # If it's not a dict, it's likely meant to be a system message
                    # Send it via the dedicated API instead of inline
                    if not isinstance(response_chunk, dict):
                        send_system_message(
                            session_id=session_id,
                            message_type="status_update",
                            content=str(response_chunk)
                        )
                        # Skip yielding this chunk in the chat stream
                        continue
                    
                    # If this is a system message, send it through the dedicated API
                    if response_chunk.get('type') == 'system':
                        # Convert to system message format and send via API
                        send_system_message(
                            session_id=session_id,
                            message_type=response_chunk.get('action', 'status_update'),
                            content={
                                "status": response_chunk.get('status', 'info'),
                                "message": response_chunk.get('content', ''),
                                "timestamp": response_chunk.get('timestamp', datetime.now().isoformat())
                            }
                        )
                        # Skip yielding system messages in the chat stream
                        continue
                    
                    # For regular chat messages, include session_id
                    if 'session_id' not in response_chunk:
                        response_chunk['session_id'] = session_id
                        
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
                    'session_id': session_id
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

# Search status is now handled via streaming system messages
