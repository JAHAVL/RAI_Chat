#!/usr/bin/env python3
"""
Direct test script to send a message to the backend API and verify the response.
This tests the entire flow from backend to LLM Engine and back.

Modified to work with the unified permission system in Docker environment.
"""

import requests
import json
import uuid
import time

# Configuration
BACKEND_URL = "http://localhost:6102"
DEBUG = True
TEST_MESSAGE = "Hello, can you tell me about yourself? What is RAI Chat?"

# Test user information - must match a user in the database
TEST_USER_ID = 123
TEST_USERNAME = "testuser123"

def send_test_message():
    """Send a test message to the backend API"""
    print(f"Sending test message as {TEST_USERNAME} (ID: {TEST_USER_ID}): '{TEST_MESSAGE}'")
    
    # Set up headers for authentication with our test user
    auth_headers = {
        "Content-Type": "application/json",
        "X-Test-User-ID": str(TEST_USER_ID),
        "X-Test-Username": TEST_USERNAME
    }
    
    # Debug information
    if DEBUG:
        print(f"Backend URL: {BACKEND_URL}")
        print("Testing connection to backend...")
        try:
            health_response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
            print(f"Backend health check: {health_response.status_code}")
            print(f"Response: {health_response.text}")
        except Exception as e:
            print(f"Backend health check failed: {str(e)}")
    
    # First create a session
    session_payload = {
        "title": f"Test Session {time.strftime('%Y%m%d-%H%M%S')}"
    }
    
    try:
        # Create a new session using the session API
        session_response = requests.post(
            f"{BACKEND_URL}/api/sessions/create",
            headers=auth_headers,
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
            print(f"Response: {session_response.text}")
            return False
            
        print(f"Session created successfully with ID: {session_id}")
        
        # Now send a message with stream=True to handle the NDJSON response
        message_payload = {
            "session_id": session_id,
            "message": TEST_MESSAGE
        }
        
        print("Sending message to LLM Engine...")
        # Use stream=True to process the response as it comes in
        message_response = requests.post(
            f"{BACKEND_URL}/api/chat",
            headers=auth_headers,
            json=message_payload,
            stream=True,  # Important for NDJSON streaming response
            timeout=60
        )
        
        if message_response.status_code != 200:
            print(f"Failed to send message: {message_response.status_code}")
            print(f"Response: {message_response.text}")
            return False
        
        print("\n=== Message Response ===")
        full_response = ""
        # Process the streaming response
        for line in message_response.iter_lines():
            if not line:  # Skip empty lines
                continue
            
            try:
                # Decode the line and parse as JSON
                decoded_line = line.decode('utf-8')
                chunk = json.loads(decoded_line)
                
                # Check for different chunk types
                if chunk.get('type') == 'connection_established':
                    print("Connection established with server...")
                elif chunk.get('type') == 'content':
                    content = chunk.get('content', '')
                    print(f"Content: {content}")
                    full_response += content  # Accumulate content
                elif chunk.get('type') == 'error':
                    print(f"Error: {chunk.get('content')}")
                else:
                    # For any other chunk types
                    content = chunk.get('content', chunk)
                    print(f"Response chunk: {content}")
                    if isinstance(content, str):
                        full_response += content  # Accumulate content
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print(f"Raw line: {line.decode('utf-8')}")
            except Exception as e:
                print(f"Error processing response chunk: {e}")
        
        print(f"\nFull response: {full_response}")
        
        # Check if we got a meaningful response
        if len(full_response) > 20:
            print("\n✓ SUCCESS: Received a valid response from the LLM Engine")
            return True
        else:
            print("\n✗ FAILURE: Response too short or empty")
            return False
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    result = send_test_message()
    if result:
        print("\nTest completed successfully! The entire message flow is working.")
        exit(0)
    else:
        print("\nTest failed. Please check the logs for more information.")
        exit(1)
