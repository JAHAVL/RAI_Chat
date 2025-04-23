# Test endpoint for direct web search testing
import logging
import os
from flask import Blueprint, jsonify, request
from core.auth.utils import token_required
from tavily import TavilyClient

test_search_bp = Blueprint('test_search', __name__, url_prefix='/api/test-search')
logger = logging.getLogger(__name__)

@test_search_bp.route('', methods=['POST'])
@token_required
def test_direct_search():
    """Simple test endpoint to directly execute a web search and return results"""
    try:
        # Extract query from request
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'No query provided'
            }), 400
        
        # Get API key from environment
        tavily_api_key = os.environ.get('TAVILY_API_KEY')
        if not tavily_api_key:
            return jsonify({
                'status': 'error',
                'message': 'Tavily API key not configured'
            }), 500
        
        # Initialize client
        logger.info(f"Initializing Tavily client with API key starting with {tavily_api_key[:4]}...")
        client = TavilyClient(api_key=tavily_api_key)
        
        # Execute search
        logger.info(f"Performing search for query: '{query}'")
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=True,
            include_images=False,
            include_raw_content=False
        )
        
        # Format the results
        formatted_results = f"Search results for: {query}\n\n"
        
        # Include Tavily's answer if available
        if response.get('answer'):
            formatted_results += f"Summary: {response['answer']}\n\n"
        
        # Include individual search results
        if response.get('results'):
            for i, result in enumerate(response['results'], 1):
                formatted_results += f"{i}. {result['title']}\n"
                formatted_results += f"   URL: {result['url']}\n"
                formatted_results += f"   {result.get('content', 'No content available')[:200]}...\n\n"
        else:
            formatted_results += "No search results found. Please try a different query.\n"
        
        logger.info(f"Search completed successfully with {len(response.get('results', []))} results")
        
        # Return the raw response and formatted results
        return jsonify({
            'status': 'success',
            'raw_response': response,
            'formatted_results': formatted_results
        })
    
    except Exception as e:
        logger.error(f"Error during test search: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"Error during search: {str(e)}"
        }), 500
