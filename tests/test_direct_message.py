#!/usr/bin/env python3
"""
Direct test script to send a message to the backend API and verify the response.
This tests the entire flow from backend to LLM Engine and back.
"""

import requests
import json
import uuid
import time

# Configuration
BACKEND_URL = "http://localhost:6102"
DEBUG = True
TEST_MESSAGE = "Hello, can you tell me about yourself? What is RAI Chat?"

def send_test_message():
    """Send a test message to the backend API"""
    print(f"Sending test message: '{TEST_MESSAGE}'")
    
    # Create a unique session ID
    session_id = str(uuid.uuid4())
    print(f"Using session ID: {session_id}")
    
    # Debug information
    if DEBUG:
        print(f"Backend URL: {BACKEND_URL}")
        print("Testing connection to backend...")
        try:
            health_response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
            print(f"Backend health check: {health_response.status_code}")
        except Exception as e:
            print(f"Backend health check failed: {str(e)}")
    
    # First create a session
    session_payload = {
        "session_id": session_id,
        "user_id": "test_user"
    }
    
    try:
        session_response = requests.post(
            f"{BACKEND_URL}/api/sessions",
            json=session_payload,
            timeout=10
        )
        
        if session_response.status_code != 200:
            print(f"Failed to create session: {session_response.status_code}")
            print(f"Response: {session_response.text}")
            return False
            
        print("Session created successfully")
        
        # Now send a message
        message_payload = {
            "session_id": session_id,
            "message": TEST_MESSAGE
        }
        
        message_response = requests.post(
            f"{BACKEND_URL}/api/chat",
            json=message_payload,
            timeout=60  # Longer timeout for LLM processing
        )
        
        if message_response.status_code != 200:
            print(f"Failed to send message: {message_response.status_code}")
            print(f"Response: {message_response.text}")
            return False
            
        # Parse and display the response
        result = message_response.json()
        print("\n=== Message Response ===")
        print(f"Status: {result.get('status', 'unknown')}")
        
        # Extract and print the response content
        response_text = result.get('response', 'No response')
        print(f"\nResponse: {response_text}")
        
        # Check if we got a meaningful response
        if len(response_text) > 20:
            print("\n✅ SUCCESS: Received a valid response from the LLM")
            return True
        else:
            print("\n❌ FAILURE: Response too short or empty")
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
