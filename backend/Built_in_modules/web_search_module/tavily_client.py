"""
Client for interacting with the Tavily Search API.
"""
import os
import logging
from tavily import TavilyClient
from RAI_Chat.backend.config import AppConfig  # Import from the correct path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Tavily Client
tavily_api_key = AppConfig.TAVILY_API_KEY
if not tavily_api_key:
    logger.warning("TAVILY_API_KEY environment variable not set. Web search functionality will be disabled.")
    tavily_client = None
else:
    try:
        tavily_client = TavilyClient(api_key=tavily_api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Tavily client: {e}")
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