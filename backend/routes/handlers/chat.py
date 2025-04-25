"""
Chat handlers for API routes.

This module contains handlers for chat messages, search, and related functionality.
"""

import logging
import re
import json
from flask import request, g, jsonify
from managers.user_session_manager import UserSessionManager
from components.action_handler import perform_search
from .common import create_error_response, create_success_response, stream_response

# Create logger
logger = logging.getLogger(__name__)

def handle_chat():
    """Handler for chat messages - supports both standard and streaming responses"""
    try:
        # Get user info and request data
        user_id = g.user['user_id']
        username = g.user['username']
        data = request.get_json()
        
        # Validate request
        if not data or 'message' not in data:
            return create_error_response('No message provided')
        
        # Extract parameters
        user_input = data['message']
        session_id = data.get('session_id')
        streaming = data.get('streaming', False)
        
        # Direct search handling
        search_match = re.search(r"\[SEARCH:\s*(.+?)\s*\]", user_input)
        if search_match:
            return handle_search(search_match.group(1).strip(), session_id)
        
        # Get conversation manager
        session_id, conversation_manager = UserSessionManager.get_conversation_manager_for_user_session(user_id, session_id)
        
        # Process message
        if streaming:
            # Return streaming response
            return stream_response(conversation_manager.process_message(user_input, session_id))
        else:
            # Collect all chunks for a single response
            chunks = list(conversation_manager.process_message(user_input, session_id))
            
            # Return the last (final) chunk as a regular JSON response
            if chunks:
                final_chunk = chunks[-1]
                logger.info(f"Final response being sent to frontend: {json.dumps(final_chunk)}")
                return jsonify(final_chunk), 200
            else:
                return create_error_response('No response generated')
                
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        return create_error_response(f'Error processing request: {str(e)}', 500)

def handle_chat_stream():
    """Handler for streaming chat messages"""
    try:
        # Get user info and request data
        user_id = g.user['user_id']
        data = request.get_json()
        
        # Validate request
        if not data or 'message' not in data:
            return create_error_response('No message provided')
        
        # Extract parameters
        user_input = data['message']
        session_id = data.get('session_id')
        
        # Get conversation manager
        session_id, conversation_manager = UserSessionManager.get_conversation_manager_for_user_session(user_id, session_id)
        
        # Return streaming response
        return stream_response(conversation_manager.process_message(user_input, session_id))
    except Exception as e:
        logger.error(f"Error processing streaming chat request: {str(e)}", exc_info=True)
        return create_error_response(f'Error processing request: {str(e)}', 500)

def handle_search(query, session_id=None):
    """Handler for search queries"""
    try:
        user_id = g.user['user_id']
        
        # Define generator function for streaming search results
        def search_response_generator():
            try:
                # Get conversation manager
                session_id_to_use, conversation_manager = UserSessionManager.get_conversation_manager_for_user_session(user_id, session_id)
                
                # Start the search
                search_message = f"Searching for: {query}"
                yield json.dumps({
                    'type': 'search_start', 
                    'content': search_message,
                    'session_id': session_id_to_use
                }) + "\n"
                
                # Perform the search
                search_results = perform_search(query, conversation_manager)
                
                # Process search results
                if search_results:
                    # Format the results
                    formatted_results = conversation_manager.format_search_results(search_results)
                    yield json.dumps({
                        'type': 'search_results', 
                        'content': formatted_results,
                        'raw_results': search_results,
                        'session_id': session_id_to_use
                    }) + "\n"
                else:
                    # No results found
                    yield json.dumps({
                        'type': 'search_results', 
                        'content': "No results found for your search query.",
                        'raw_results': [],
                        'session_id': session_id_to_use
                    }) + "\n"
                    
            except Exception as e:
                # Handle any errors during search
                logger.error(f"Error in search generator: {str(e)}", exc_info=True)
                yield json.dumps({
                    'type': 'error', 
                    'content': f"Error during search: {str(e)}"
                }) + "\n"
        
        # Return streaming response with search generator
        return stream_response(search_response_generator())
        
    except Exception as e:
        logger.error(f"Error processing search request: {str(e)}", exc_info=True)
        return create_error_response(f'Error processing search request: {str(e)}', 500)
