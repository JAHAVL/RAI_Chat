#!/usr/bin/env python3
"""
Demonstration of the web search integration in RAI Chat

This test specifically demonstrates the web search functionality
that we've implemented and fixed in the backend.
"""

import requests
import json
import time
import uuid

# Configuration
BACKEND_URL = "http://localhost:6102"
TEST_USER_ID = 123
TEST_USERNAME = "testuser123"

# Auth headers to use for all requests
AUTH_HEADERS = {
    "Content-Type": "application/json",
    "X-Test-User-ID": str(TEST_USER_ID),
    "X-Test-Username": TEST_USERNAME
}

def test_direct_web_search():
    """Test the direct web search functionality"""
    print("\n===== Testing Direct Web Search =====\n")
    
    # Create a new test session
    session_payload = {
        "title": f"Web Search Demo {time.strftime('%Y%m%d-%H%M%S')}"
    }
    
    try:
        # Create a new session
        session_response = requests.post(
            f"{BACKEND_URL}/api/sessions/create",
            headers=AUTH_HEADERS,
            json=session_payload,
            timeout=10
        )
        
        if session_response.status_code != 200:
            print(f"\u274c Failed to create session: {session_response.status_code}")
            print(f"Response: {session_response.text}")
            return False
        
        session_data = session_response.json()
        session_id = session_data.get("session_id")
        
        if not session_id:
            print("\u274c No session ID returned")
            return False
            
        print(f"\u2713 Session created successfully with ID: {session_id}")
        
        # Prepare the search query
        search_query = "What are the features of GPT-4?"
        
        # Format the message with search directive
        message = f"[SEARCH: {search_query}]"
        
        print(f"Sending search query: '{search_query}'")
        
        chat_payload = {
            "message": message,
            "session_id": session_id
        }
        
        # Send the chat request with stream=True to get a streaming response
        chat_response = requests.post(
            f"{BACKEND_URL}/api/chat",
            headers=AUTH_HEADERS,
            json=chat_payload,
            stream=True,
            timeout=60
        )
        
        if chat_response.status_code != 200:
            print(f"\u274c Chat request failed: {chat_response.status_code}")
            print(f"Response: {chat_response.text}")
            return False
        
        # Process the streaming response
        print("\nProcessing streaming response...")
        search_results = None
        
        for line in chat_response.iter_lines():
            if not line:
                continue
                
            try:
                # Decode and parse the JSON chunk
                chunk = json.loads(line.decode('utf-8'))
                
                # Extract type and content
                chunk_type = chunk.get('type')
                
                # Print chunk information
                if chunk_type == "connection_established":
                    print(f"Received chunk type: {chunk_type}")
                elif chunk_type == "system" and chunk.get('action') == 'web_search':
                    status = chunk.get('status')
                    if status == 'active':
                        print(f"\nWeb search initiated: {chunk.get('content')}")
                    elif status == 'complete':
                        search_results = chunk.get('content')
                        print(f"\nSearch completed!\n")
                        print(f"{search_results}\n")
                elif chunk_type == "content":
                    print(f"Received content: {chunk.get('content')[:100]}..." if len(chunk.get('content', '')) > 100 else chunk.get('content'))
                    
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                continue
        
        if search_results:
            print("\n\u2713 Successfully received web search results")
            return True
        else:
            print("\n\u274c No web search results received")
            return False
            
    except Exception as e:
        print(f"\u274c Error testing web search: {e}")
        return False

if __name__ == "__main__":
    test_direct_web_search()
