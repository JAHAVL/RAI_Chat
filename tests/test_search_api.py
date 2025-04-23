#!/usr/bin/env python3
"""
Comprehensive web search integration test

This test focuses specifically on the web search API integration:
1. Tests the direct API endpoint (/api/test-search)
2. Tests the search system message API
3. Tests the end-to-end integration with a real search query
"""

import requests
import json
import time
import uuid

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

def test_direct_search_api():
    """Test the direct search API endpoint"""
    print("\n===== Testing Direct Search API =====\n")
    
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
        
        if response.status_code != 200:
            print(f"\u274c Direct search API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Parse the response
        result = response.json()
        print(f"\u2713 Direct search API returned status: {result.get('status')}")
        
        # Check for search results
        formatted_results = result.get('formatted_results', '')
        if len(formatted_results) > 100 and "Paris" in formatted_results:
            print(f"\u2713 Direct search API returned valid results ({len(formatted_results)} chars)")
            return True
        else:
            print(f"\u274c Direct search API returned invalid results")
            return False
            
    except Exception as e:
        print(f"\u274c Error testing direct search API: {e}")
        return False

def test_system_messages_api():
    """Test the system messages API for storing search results"""
    print("\n===== Testing System Messages API =====\n")
    
    # Create a session
    session_payload = {
        "title": f"System Messages Test {time.strftime('%Y%m%d-%H%M%S')}"
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
        
        # Create a system message for search
        message_payload = {
            "session_id": session_id,
            "message_type": "web_search",
            "content": json.dumps({
                "status": "active",
                "message": f"Searching for: {TEST_QUERY}",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            })
        }
        
        # Send the system message
        message_response = requests.post(
            f"{BACKEND_URL}/api/system-messages",
            headers=AUTH_HEADERS,
            json=message_payload,
            timeout=10
        )
        
        if message_response.status_code != 200:
            print(f"\u274c Failed to create system message: {message_response.status_code}")
            print(f"Response: {message_response.text}")
            return False
        
        message_data = message_response.json()
        message_id = message_data.get("id")
        
        if not message_id:
            print("\u274c No message ID returned")
            return False
            
        print(f"\u2713 System message created successfully with ID: {message_id}")
        
        # Now retrieve the message to verify it was stored
        retrieve_response = requests.get(
            f"{BACKEND_URL}/api/system-messages/session/{session_id}",
            headers=AUTH_HEADERS,
            timeout=10
        )
        
        if retrieve_response.status_code != 200:
            print(f"\u274c Failed to retrieve system messages: {retrieve_response.status_code}")
            print(f"Response: {retrieve_response.text}")
            return False
        
        retrieve_data = retrieve_response.json()
        messages = retrieve_data.get("messages", [])
        
        if not messages:
            print("\u274c No messages returned")
            return False
        
        print(f"\u2713 Successfully retrieved {len(messages)} system messages")
        
        # Check if our message is in the list
        found = False
        for msg in messages:
            if msg.get("id") == message_id:
                found = True
                print("\u2713 Found our system message in the list")
                break
        
        if not found:
            print("\u274c Our system message was not found in the list")
            return False
        
        # Now update the message
        update_payload = {
            "id": message_id,
            "content": json.dumps({
                "status": "complete",
                "message": f"Search results for: {TEST_QUERY}",
                "results": "Paris is famous for the Eiffel Tower and the Louvre Museum.",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
            })
        }
        
        update_response = requests.put(
            f"{BACKEND_URL}/api/system-messages/{message_id}",
            headers=AUTH_HEADERS,
            json=update_payload,
            timeout=10
        )
        
        if update_response.status_code != 200:
            print(f"\u274c Failed to update system message: {update_response.status_code}")
            print(f"Response: {update_response.text}")
            return False
        
        print("\u2713 Successfully updated system message")
        
        return True
        
    except Exception as e:
        print(f"\u274c Error testing system messages API: {e}")
        return False

def test_direct_web_search():
    """Test direct web search via an API endpoint that specifically handles web search"""
    print("\n===== Testing Direct Web Search Integration =====\n")  
    
    # First, let's create a session
    session_payload = {
        "title": f"Web Search Integration Test {time.strftime('%Y%m%d-%H%M%S')}"
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
        
        # Create a direct web search message that contains the [SEARCH:] tag
        search_message = f"[SEARCH: {TEST_QUERY}]"
        
        message_payload = {
            "session_id": session_id,
            "message": search_message
        }
        
        # Send the message
        print(f"Sending message with search tag: '{search_message}'")
        
        # Send the message with stream=True to handle the streaming response
        message_response = requests.post(
            f"{BACKEND_URL}/api/chat",
            headers=AUTH_HEADERS,
            json=message_payload,
            stream=True,
            timeout=30
        )
        
        if message_response.status_code != 200:
            print(f"\u274c Failed to send message: {message_response.status_code}")
            print(f"Response: {message_response.text}")
            return False
        
        print("Processing streaming response...")
        
        search_initiated = False
        search_results_received = False
        
        # Process the streaming response
        for line in message_response.iter_lines():
            if not line:  # Skip empty lines
                continue
            
            try:
                # Decode the line and parse as JSON
                decoded_line = line.decode('utf-8')
                
                # Skip non-JSON lines
                if not decoded_line.strip() or decoded_line.strip() == "data:":
                    continue
                
                try:
                    chunk = json.loads(decoded_line)
                    print(f"Received chunk type: {chunk.get('type', 'unknown')}")
                    
                    # Check for search-related chunks
                    if chunk.get('type') == 'system' and chunk.get('action') == 'web_search':
                        search_initiated = True
                        print(f"Web search initiated: {chunk.get('content')}")
                        
                        # Check if this chunk includes search results
                        content = chunk.get('content', '')
                        if isinstance(content, str) and len(content) > 100 and ('Search results' in content or 'Paris' in content):
                            search_results_received = True
                            print(f"Search results received (sample): {content[:100]}...")
                    
                    # Check for content chunks that might contain search results
                    elif chunk.get('type') == 'content':
                        content = chunk.get('content', '')
                        print(f"Content: {content[:50]}..." if len(content) > 50 else f"Content: {content}")
                        
                        if 'search' in content.lower() and ('Paris' in content or 'Eiffel' in content):
                            search_results_received = True
                    
                except json.JSONDecodeError:
                    print(f"Non-JSON line: {decoded_line[:50]}...")
                    continue
                    
            except Exception as e:
                print(f"Error processing response chunk: {e}")
        
        # Check if the search worked
        if search_initiated:
            print("\u2713 Web search was initiated")
        else:
            print("\u274c Web search was NOT initiated")
            
        if search_results_received:
            print("\u2713 Search results were returned")
        else:
            # As a fallback, check system messages API for search results
            print("Checking system messages API for search results...")
            
            system_response = requests.get(
                f"{BACKEND_URL}/api/system-messages/session/{session_id}",
                headers=AUTH_HEADERS,
                timeout=10
            )
            
            if system_response.status_code == 200:
                system_data = system_response.json()
                messages = system_data.get("messages", [])
                
                for msg in messages:
                    if msg.get("message_type") == "web_search":
                        # Try to parse the content as JSON
                        content = msg.get("content", "{}")
                        if isinstance(content, str):
                            try:
                                content_obj = json.loads(content)
                                if content_obj.get("status") == "complete":
                                    search_results_received = True
                                    print("\u2713 Search results found in system messages")
                                    break
                            except:
                                # If it's not JSON, check if it contains search results directly
                                if "search results" in content.lower() and len(content) > 100:
                                    search_results_received = True
                                    print("\u2713 Search results found in system messages (raw)")
                                    break
            
        if search_initiated and search_results_received:
            print("\n\u2705 WEB SEARCH INTEGRATION TEST PASSED")
            return True
        else:
            print("\n\u274c WEB SEARCH INTEGRATION TEST FAILED")
            return False
            
    except Exception as e:
        print(f"\u274c Error testing direct web search: {e}")
        return False

def run_all_tests():
    """Run all web search integration tests"""
    print("\n***** RUNNING WEB SEARCH INTEGRATION TESTS *****\n")
    
    # Run the tests
    direct_api_success = test_direct_search_api()
    system_messages_success = test_system_messages_api()
    integration_success = test_direct_web_search()
    
    # Display results
    print("\n***** TEST RESULTS SUMMARY *****")
    print(f"Direct Search API Test: {'\u2705 PASSED' if direct_api_success else '\u274c FAILED'}")
    print(f"System Messages API Test: {'\u2705 PASSED' if system_messages_success else '\u274c FAILED'}")
    print(f"Web Search Integration Test: {'\u2705 PASSED' if integration_success else '\u274c FAILED'}")
    
    # Overall result
    if direct_api_success and system_messages_success and integration_success:
        print("\n\u2705 ALL WEB SEARCH INTEGRATION TESTS PASSED")
        return True
    else:
        failed_count = sum(not x for x in [direct_api_success, system_messages_success, integration_success])
        print(f"\n\u274c {failed_count}/3 TESTS FAILED")
        return False

if __name__ == "__main__":
    run_all_tests()
