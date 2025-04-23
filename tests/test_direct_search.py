#!/usr/bin/env python3
"""
Test script to specifically test the web search functionality in the RAI Chat backend.
This script directly sends a message designed to trigger a web search.
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

def test_web_search():
    print("\n===== Testing Web Search Integration =====\n")
    
    # First, run a direct test to confirm Tavily is working
    print("First, verifying direct Tavily functionality...")
    direct_test_cmd = "python tests/test_tavily_direct.py"
    import subprocess
    result = subprocess.run(direct_test_cmd, shell=True)
    if result.returncode != 0:
        print("\nDirect Tavily test failed. Please fix Tavily integration first.")
        return False
        
    print("\nDirect Tavily test succeeded. Now testing LLM integration...")
    
    # Create a session
    session_payload = {
        "title": f"Web Search Test {time.strftime('%Y%m%d-%H%M%S')}"
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
            print(f"Failed to create session: {session_response.status_code}")
            print(f"Response: {session_response.text}")
            return False
        
        session_data = session_response.json()
        session_id = session_data.get("session_id")
        
        if not session_id:
            print("No session ID returned")
            return False
            
        print(f"Session created successfully with ID: {session_id}")
        
        # This is our direct approach: bypass the LLM and use our test endpoint
        print("\nNow directly testing web search through the test endpoint...")
        test_payload = {
            "query": "What is Paris famous for?"
        }
        
        test_response = requests.post(
            f"{BACKEND_URL}/api/test-search",
            headers=AUTH_HEADERS,
            json=test_payload,
            timeout=20
        )
        
        if test_response.status_code != 200:
            print(f"Direct test endpoint failed: {test_response.status_code}")
            print(f"Response: {test_response.text}")
            return False
        
        test_result = test_response.json()
        if test_result.get('status') == 'success':
            print("\u2713 Direct API test confirmed web search is working")
        else:
            print("\u2717 Direct API test failed")
            return False
        
        # Very explicit message to trigger web search
        search_message = "I need information about Paris. Please do a web search with the exact search term [SEARCH: What is Paris famous for]"
        
        message_payload = {
            "session_id": session_id,
            "message": search_message
        }
        
        print(f"\nSending search trigger message: '{search_message}'")
        
        # Send the message with stream=True to handle the streaming response
        message_response = requests.post(
            f"{BACKEND_URL}/api/chat",
            headers=AUTH_HEADERS,
            json=message_payload,
            stream=True,
            timeout=60
        )
        
        if message_response.status_code != 200:
            print(f"Failed to send message: {message_response.status_code}")
            print(f"Response: {message_response.text}")
            return False
        
        print("\n--- Streaming Response ---")
        full_response = ""
        search_initiated = False
        search_results_received = False
        search_content = ""
        
        # Process the streaming response
        for line in message_response.iter_lines():
            if not line:  # Skip empty lines
                continue
            
            try:
                # Decode the line and parse as JSON
                decoded_line = line.decode('utf-8')
                
                # Skip non-JSON lines (like the initial connection line)
                if not decoded_line.strip() or decoded_line.strip() == "data:":
                    continue
                    
                # Special handling for system messages
                if "system_messages" in decoded_line:
                    print(f"System message detected: {decoded_line}")
                    search_initiated = True
                    continue
                
                # Parse the JSON
                try:
                    chunk = json.loads(decoded_line)
                except json.JSONDecodeError:
                    print(f"Non-JSON line: {decoded_line}")
                    continue
                
                # Check for different chunk types
                chunk_type = chunk.get('type', 'unknown')
                
                if chunk_type == 'connection_established':
                    print("Connection established with server...")
                    
                elif chunk_type == 'system':
                    search_initiated = True
                    if chunk.get('action') == 'web_search':
                        print(f"Web search detected: {chunk.get('content')}")
                        search_content = chunk.get('content', '')
                        if search_content and len(search_content) > 50:
                            search_results_received = True
                            print(f"Search results sample: {search_content[:100]}...")
                    
                elif chunk_type == 'content':
                    content = chunk.get('content', '')
                    print(f"Content: {content[:100]}..." if len(content) > 100 else f"Content: {content}")
                    full_response += content
                    if 'search results' in content.lower():
                        search_results_received = True
                        
                elif chunk_type == 'final':
                    content = json.dumps(chunk, indent=2)[:200]
                    print(f"Final response: {content}...")
                    
                    # Check if response contains search results
                    if 'search results' in str(chunk).lower():
                        search_results_received = True
                        
                else:
                    # For any other chunk types
                    print(f"Response chunk ({chunk_type}): {str(chunk)[:100]}...")
                    
                    # Check for search results in any part of the response
                    if 'search results' in str(chunk).lower() or 'tavily' in str(chunk).lower():
                        search_results_received = True
                    
            except Exception as e:
                print(f"Error processing response chunk: {e}")
        
        # Also check system messages directly
        try:
            print("\nChecking system messages directly...")
            system_response = requests.get(
                f"{BACKEND_URL}/api/system-messages/session/{session_id}",
                headers=AUTH_HEADERS,
                timeout=10
            )
            
            if system_response.status_code == 200:
                system_data = system_response.json()
                messages = system_data.get('messages', [])
                
                if messages:
                    print(f"Found {len(messages)} system messages")
                    for msg in messages:
                        if msg.get('message_type') == 'web_search':
                            search_initiated = True
                            content = msg.get('content', {})
                            if isinstance(content, str):
                                try:
                                    content = json.loads(content)
                                except:
                                    pass
                                    
                            if isinstance(content, dict) and content.get('status') == 'complete':
                                search_results_received = True
                                print(f"Found completed web search in system messages")
            else:
                print(f"Failed to fetch system messages: {system_response.status_code}")
                
        except Exception as e:
            print(f"Error checking system messages: {e}")
        
        print("\n--- Search Test Results ---")
        if search_initiated:
            print("\u2713 Web search was successfully initiated")
        else:
            print("\u2717 Web search was NOT initiated")
            
        if search_results_received:
            print("\u2713 Search results were successfully returned")
        else:
            print("\u2717 Search results were NOT returned")
            
        if search_initiated and search_results_received:
            print("\n\u2705 WEB SEARCH INTEGRATION TEST PASSED")
            return True
        else:
            print("\n\u274c WEB SEARCH INTEGRATION TEST FAILED")
            return False
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    test_web_search()
