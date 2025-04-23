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

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

@chat_bp.route('', methods=['POST'])
@token_required
def chat():
    """Chat endpoint using conversation manager, supporting streaming"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'message' not in data:
            return jsonify({
                'error': 'Message is required',
                'status': 'error'
            }), 400
        
        user_input = data.get('message')
        session_id = data.get('session_id')  # Optional
        streaming = data.get('streaming', False)  # Default to non-streaming
        
        # Get user ID from auth token
        user_id = g.user_id
        
        # Get database session
        from ..core.database.session import get_db
        db = get_db()
        
        # Get user session manager
        user_session_manager = get_user_session_manager(user_id)
        
        # Let the LLM decide if a web search is necessary
        
        # Get conversation manager - this returns a tuple (session_id, conversation_manager)
        actual_session_id, conversation_manager = user_session_manager.get_conversation_manager(user_id, session_id)
        
        # Check if we got a valid conversation manager
        if not conversation_manager:
            logger.error(f"Failed to get conversation manager for user {user_id}, session {session_id}")
            return jsonify({"error": "Failed to initialize conversation manager"}), 500
            
        # Update session_id with the actual one returned
        session_id = actual_session_id
        
        # Load or create session
        if session_id:
            conversation_manager.load_chat(session_id)
        else:
            conversation_manager.start_new_chat()
            session_id = conversation_manager.current_session_id
        
        # Process the message through the conversation manager with streaming response
        def generate_response():
            try:
                logger.info(f"Processing message for user {user_id}, session {actual_session_id}")
                
                # Collect stream chunks
                saw_search_status = False
                
                for response_chunk in conversation_manager.process_message(user_input, actual_session_id):
                    logger.info(f"--- Yielding chunk: {response_chunk} ---")
                    
                    # Pass through system messages as-is
                    if response_chunk.get('type') == 'system':
                        logger.info(f"*** SYSTEM MESSAGE: {response_chunk.get('action', 'GENERAL')} ***")
                        # Make sure it's flushed immediately to the client
                        yield json.dumps(response_chunk) + '\n'
                    elif response_chunk.get('type') == 'final':
                        # For final responses, extract just the content
                        final_content = None
                        
                        # Extract content using the same priority order as non-streaming
                        if 'llm_response' in response_chunk and isinstance(response_chunk['llm_response'], dict):
                            # Priority 1: Get content from tier3 if available
                            if 'response_tiers' in response_chunk['llm_response']:
                                tier3 = response_chunk['llm_response']['response_tiers'].get('tier3')
                                if tier3:
                                    final_content = tier3
                            
                            # Priority 2: Fall back to direct response field if no tier3
                            if not final_content and 'response' in response_chunk['llm_response']:
                                final_content = response_chunk['llm_response']['response']
                        
                        # Priority 3: Check for content/response at the top level
                        if not final_content:
                            final_content = response_chunk.get('content') or response_chunk.get('response')
                        
                        # Create minimal response
                        clean_chunk = {
                            'type': 'final',
                            'content': final_content or "Sorry, I couldn't generate a proper response.",
                            'session_id': response_chunk.get('session_id', actual_session_id),
                            'timestamp': response_chunk.get('timestamp', datetime.utcnow().isoformat())
                        }
                        
                        logger.info(f"Yielding clean final response")
                        yield json.dumps(clean_chunk) + '\n'
                    else:
                        # Yield all other chunks normally
                        yield json.dumps(response_chunk) + '\n'
                    
                # Save after all chunks are processed
                logger.info(f"--- Attempting to save session {actual_session_id} via CM.save_current_chat ---")
                conversation_manager.save_current_chat()
                logger.info(f"--- Finished CM.save_current_chat successfully for session {actual_session_id} ---")
            except Exception as e:
                logger.error(f"Error in generate_response: {e}")
                yield json.dumps({"status": "error", "message": f"Error processing request: {str(e)}"}) + '\n'
        
        # Handle streaming response if requested
        if streaming:
            def stream_response():
                for update in generate_response():
                    # Convert update to JSON string and yield
                    yield update
            
            # Create streaming response
            return Response(
                stream_response(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Non-streaming response
            response_data = None
            for update in conversation_manager.get_response(db, user_input):
                response_data = update
            
            # Save the chat after processing
            conversation_manager.save_current_chat(db)
            
            # Check if we're stuck in a 'searching' state but no actual search results returned
            if response_data and 'status' in response_data and response_data.get('status') == 'searching':
                logger.info("Detected a search request, processing directly...")
                try:
                    # Import Tavily directly here to bypass potential import issues
                    from pathlib import Path
                    from dotenv import load_dotenv
                    
                    # Load env variables from various possible locations
                    backend_dir = Path(__file__).resolve().parent.parent
                    env_paths = [
                        backend_dir / '.env',
                        backend_dir / 'Backend' / '.env',
                        backend_dir / 'backend' / '.env',
                        backend_dir.parent / '.env',
                    ]
                    
                    for env_path in env_paths:
                        if env_path.exists():
                            logger.info(f"Loading .env from: {env_path}")
                            load_dotenv(dotenv_path=env_path)
                            break
                    
                    import os
                    from tavily import TavilyClient
                    
                    # Get Tavily API key from environment
                    tavily_api_key = os.environ.get('TAVILY_API_KEY')
                    if not tavily_api_key:
                        logger.error("Missing Tavily API key")
                        return jsonify({
                            'response': "I couldn't perform the web search because the Tavily API key is missing. Please contact the administrator.",
                            'session_id': session_id,
                            'status': 'search_error'
                        })
                    
                    # Get the search query from the response data
                    search_query = response_data.get('query')
                    if not search_query:
                        search_query = "latest information" # Fallback
                    
                    logger.info(f"Performing direct Tavily search for: {search_query}")
                    
                    # Perform the search
                    client = TavilyClient(api_key=tavily_api_key)
                    search_response = client.search(
                        query=search_query,
                        search_depth="basic",
                        max_results=5,
                        include_answer=True,
                        include_images=False,
                        include_raw_content=False
                    )
                    
                    # Format the search results
                    formatted_results = f"Search results for: {search_query}\n\n"
                    
                    # Include Tavily's answer if available
                    if search_response.get('answer'):
                        formatted_results += f"Summary: {search_response['answer']}\n\n"
                    
                    # Include individual search results
                    if search_response.get('results'):
                        for i, result in enumerate(search_response['results'], 1):
                            formatted_results += f"{i}. {result['title']}\n"
                            formatted_results += f"   URL: {result['url']}\n"
                            formatted_results += f"   {result.get('content', 'No content available')[:200]}...\n\n"
                    
                    logger.info(f"Direct Tavily search completed successfully: {formatted_results[:100]}...")
                    
                    # Return the formatted results
                    return jsonify({
                        'response': f"Based on my web search, here's what I found about '{search_query}':\n\n{formatted_results}",
                        'session_id': session_id,
                        'status': 'success',
                        'llm_response': {
                            'response_tiers': {
                                'tier1': 'Web Search Results',
                                'tier2': f"Here's what I found about '{search_query}':\n\n{formatted_results[:500]}...",
                                'tier3': f"Based on my web search, here's what I found about '{search_query}':\n\n{formatted_results}"
                            }
                        }
                    })
                except Exception as search_ex:
                    logger.error(f"Error performing direct Tavily search: {search_ex}", exc_info=True)
                    return jsonify({
                        'response': f"I encountered an error while performing the web search: {str(search_ex)}",
                        'session_id': session_id,
                        'status': 'search_error'
                    })
            
            # Simplify by only returning the necessary fields to the frontend
            # This prevents the frontend from having to parse the complex response structure
            if isinstance(response_data, dict):
                # Special case for system messages
                if response_data.get('type') == 'system':
                    # Just pass system messages through as-is
                    return jsonify(response_data)
                
                # For all other responses, extract just the final content
                final_content = None
                
                # Extract content using a simple priority order
                if 'llm_response' in response_data and isinstance(response_data['llm_response'], dict):
                    # Priority 1: Get content from tier3 if available
                    if 'response_tiers' in response_data['llm_response']:
                        tier3 = response_data['llm_response']['response_tiers'].get('tier3')
                        if tier3:
                            final_content = tier3
                    
                    # Priority 2: Fall back to direct response field if no tier3
                    if not final_content and 'response' in response_data['llm_response']:
                        final_content = response_data['llm_response']['response']
                
                # Priority 3: Check for content/response at the top level
                if not final_content:
                    final_content = response_data.get('content') or response_data.get('response')
                
                # Create a minimal response object
                clean_response = {
                    'type': 'final',
                    'content': final_content or "Sorry, I couldn't generate a proper response.",
                    'session_id': session_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                logger.info(f"Sending clean response to frontend")
                return jsonify(clean_response)
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to process chat request',
            'status': 'error'
        }), 500

# Search status is now handled via streaming system messages
