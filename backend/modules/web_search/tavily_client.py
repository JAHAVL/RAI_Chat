"""
Client for interacting with the Tavily Search API.
"""
import os
import logging
import sys
import traceback
from ...config import AppConfig  # Import from the new path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import TavilyClient with detailed error handling
try:
    from tavily import TavilyClient
    logger.info("Successfully imported TavilyClient")
except ImportError as e:
    logger.error(f"Failed to import TavilyClient: {e}")
    logger.error(traceback.format_exc())
    TavilyClient = None

# Initialize Tavily Client
tavily_api_key = AppConfig.TAVILY_API_KEY
logger.info(f"Tavily API key from config: {tavily_api_key[:4]}...{tavily_api_key[-4:] if len(tavily_api_key) > 8 else ''}")
logger.info(f"Tavily API key environment variable: {os.environ.get('TAVILY_API_KEY', 'Not set')[:4]}...{os.environ.get('TAVILY_API_KEY', '')[-4:] if os.environ.get('TAVILY_API_KEY', '') and len(os.environ.get('TAVILY_API_KEY', '')) > 8 else ''}")

# Check if TavilyClient was imported successfully
if TavilyClient is None:
    logger.error("TavilyClient import failed. Web search functionality will be disabled.")
    tavily_client = None
elif not tavily_api_key or tavily_api_key == 'tavily_test_api_key_placeholder':
    logger.warning("TAVILY_API_KEY environment variable not set or using placeholder. Web search functionality will be disabled.")
    tavily_client = None
else:
    try:
        logger.info(f"Attempting to initialize Tavily client with API key: {tavily_api_key[:4]}...{tavily_api_key[-4:]}")
        tavily_client = TavilyClient(api_key=tavily_api_key)
        logger.info("Tavily client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Tavily client: {e}")
        logger.error(traceback.format_exc())
        tavily_client = None

def perform_search(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using the Tavily API.

    Args:
        query: The search query string.
        max_results: The maximum number of search results to retrieve.

    Returns:
        A formatted string containing the search results, or an error message.
    """
    if not tavily_client:
        return "Web search is disabled because the Tavily API key is not configured."

    if not query:
        return "Cannot perform web search with an empty query."

    try:
        logger.info(f"Performing Tavily search for query: '{query}'")
        # Use search_depth="advanced" for potentially better results, include_raw_content=False to keep it concise
        response = tavily_client.search(
            query=query,
            search_depth="basic", # Use "basic" for speed, "advanced" for more thorough results
            max_results=max_results,
            include_answer=False, # Set to True if you want Tavily's summarized answer
            include_images=False,
            include_raw_content=False
        )

        # Format results
        results = response.get('results', [])
        if not results:
            return f"No search results found for '{query}'."

        formatted_results = f"Search results for '{query}':\n\n"
        for i, result in enumerate(results):
            formatted_results += f"[{i+1}] {result.get('title', 'N/A')}\n"
            formatted_results += f"   URL: {result.get('url', 'N/A')}\n"
            formatted_results += f"   Snippet: {result.get('content', 'N/A')}\n\n" # 'content' usually holds the snippet

        return formatted_results.strip()

    except Exception as e:
        logger.error(f"Error during Tavily search for query '{query}': {e}")
        return f"An error occurred while searching the web for '{query}'."

# Example usage (for testing)
if __name__ == '__main__':
    test_query = "What is the latest news on AI regulation?"
    search_results = perform_search(test_query)
    print(search_results)

    test_query_no_key = "Test query without key"
    # Temporarily disable client for testing
    original_client = tavily_client
    tavily_client = None
    print(perform_search(test_query_no_key))
    tavily_client = original_client # Restore client

    print(perform_search("")) # Test empty query