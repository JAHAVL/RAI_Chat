#!/usr/bin/env python3
"""
Diagnostic script to test Tavily API configuration and connectivity.
This helps verify that the web search functionality is properly set up.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tavily_test")

# Try to locate and load environment variables
def find_env_file():
    # Check the current directory and parent directories
    current_dir = os.path.abspath(os.getcwd())
    potential_paths = [
        os.path.join(current_dir, '.env'),
        os.path.join(current_dir, 'backend/.env'),
        os.path.join(current_dir, '../backend/.env'),
        os.path.join(os.path.dirname(current_dir), '.env')
    ]
    
    for path in potential_paths:
        logger.info(f"Checking for .env at: {path}")
        if os.path.exists(path):
            logger.info(f"Found .env file at: {path}")
            load_dotenv(path)
            return path
    
    return None

# Main test function
def test_tavily_setup():
    logger.info("Starting Tavily API configuration test")
    
    # Step 1: Find and load the .env file
    env_path = find_env_file()
    if not env_path:
        logger.error("❌ Could not find .env file")
        return False
    
    # Step 2: Check if TAVILY_API_KEY is set
    tavily_api_key = os.environ.get('TAVILY_API_KEY')
    if not tavily_api_key:
        logger.error("❌ TAVILY_API_KEY is not set in the environment")
        return False
    
    logger.info(f"✓ Found TAVILY_API_KEY: {tavily_api_key[:4]}...{tavily_api_key[-4:]}")
    
    # Step 3: Try to import the Tavily client
    try:
        logger.info("Attempting to import TavilyClient...")
        from tavily import TavilyClient
        logger.info("✓ Successfully imported TavilyClient")
    except ImportError as e:
        logger.error(f"❌ Failed to import TavilyClient: {e}")
        logger.error("The 'tavily' package may not be installed. Try: pip install tavily")
        return False
    
    # Step 4: Try to initialize the client
    try:
        logger.info("Initializing Tavily client...")
        client = TavilyClient(api_key=tavily_api_key)
        logger.info("✓ Successfully initialized Tavily client")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Tavily client: {e}")
        return False
    
    # Step 5: Try a simple search query
    try:
        logger.info("Testing search with a simple query...")
        query = "What is the capital of France?"
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=3
        )
        
        # Check if we got a valid response
        if not response or not isinstance(response, dict):
            logger.error(f"❌ Received invalid response: {response}")
            return False
        
        # Check if response contains results
        if 'results' not in response or not response['results']:
            logger.error("❌ Response doesn't contain search results")
            return False
        
        # Log some results
        logger.info(f"✓ Successfully received search results")
        logger.info(f"Number of results: {len(response.get('results', []))}")
        if response.get('results'):
            logger.info(f"First result title: {response['results'][0].get('title')}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error during search test: {e}")
        return False

# Run the test if executed directly
if __name__ == "__main__":
    success = test_tavily_setup()
    
    if success:
        logger.info("\n✅ ALL TESTS PASSED - Tavily API is properly configured")
        sys.exit(0)
    else:
        logger.error("\n❌ TESTS FAILED - Tavily API configuration has issues")
        sys.exit(1)
