#!/usr/bin/env python3
"""
Direct test for the Tavily web search API integration via our dedicated test endpoint.
This bypasses the complex LLM integration to directly verify the search functionality.
"""

import requests
import json

# Configuration
BACKEND_URL = "http://localhost:6102"
TEST_USER_ID = 123
TEST_USERNAME = "testuser123"
TEST_QUERY = "What is Paris famous for?"

# Auth headers to use for all requests
AUTH_HEADERS = {
    "Content-Type": "application/json",
    "X-Test-User-ID": str(TEST_USER_ID),
    "X-Test-Username": TEST_USERNAME
}

def test_direct_tavily_search():
    print(f"\n===== Testing Direct Tavily Web Search API =====\n")
    print(f"Using query: '{TEST_QUERY}'")
    
    # Prepare the search payload
    payload = {
        "query": TEST_QUERY
    }
    
    try:
        # Send the search request
        response = requests.post(
            f"{BACKEND_URL}/api/test-search",
            headers=AUTH_HEADERS,
            json=payload,
            timeout=20
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            print(f"\n\u274c ERROR: HTTP Status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Parse and display the response
        result = response.json()
        status = result.get('status')
        
        if status != 'success':
            print(f"\n\u274c ERROR: API returned status '{status}'")
            print(f"Message: {result.get('message', 'No error message provided')}")
            return False
        
        # Display the formatted results
        formatted_results = result.get('formatted_results', '')
        print("\n--- Search Results ---\n")
        print(formatted_results)
        
        # Check if results look valid
        if len(formatted_results) > 100 and "Search results for:" in formatted_results:
            print("\n\u2705 SUCCESS: Received valid search results from Tavily API")
            
            # Display some stats about the raw response
            raw = result.get('raw_response', {})
            num_results = len(raw.get('results', []))
            answer = raw.get('answer', '')[:100] + '...' if raw.get('answer') else 'No answer provided'
            
            print(f"\nResults count: {num_results}")
            print(f"Summary: {answer}")
            
            return True
        else:
            print("\n\u274c ERROR: Search results seem incomplete or invalid")
            return False
            
    except Exception as e:
        print(f"\n\u274c ERROR: Exception during search test: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_direct_tavily_search()
    
    if success:
        print("\n\u2705 TAVILY WEB SEARCH API TEST PASSED")
        exit(0)
    else:
        print("\n\u274c TAVILY WEB SEARCH API TEST FAILED")
        exit(1)
