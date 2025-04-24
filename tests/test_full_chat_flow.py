#!/usr/bin/env python3
"""
End-to-end test of the full chat flow from backend to LLM Engine

This test sends a message through the backend to the LLM Engine
and processes the streaming response to verify the flow works correctly.
"""

import requests
import json
import time
import uuid
import sys

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

def test_full_chat_flow():
    """Test the full chat flow from backend to LLM Engine"""
    print("\n===== Testing Full Chat Flow =====\n")
    
    # Create a new test session
    session_payload = {
        "title": f"Full Chat Flow Test {time.strftime('%Y%m%d-%H%M%S')}"
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
            print(f"❌ Failed to create session: {session_response.status_code}")
            print(f"Response: {session_response.text}")
            return False
        
        session_data = session_response.json()
        session_id = session_data.get("session_id")
        
        if not session_id:
            print("❌ No session ID returned")
            return False
            
        print(f"✓ Session created successfully with ID: {session_id}")
        
        # Prepare the test message - needs modification to avoid triggering web search
        message = "Please describe the features of RAI Chat without searching the web."
        
        chat_payload = {
            "message": message,
            "session_id": session_id
        }
        
        print(f"Sending message: '{message}'")
        
        # Send the chat request with stream=True to get a streaming response
        chat_response = requests.post(
            f"{BACKEND_URL}/api/chat",
            headers=AUTH_HEADERS,
            json=chat_payload,
            stream=True,
            timeout=60
        )
        
        if chat_response.status_code != 200:
            print(f"❌ Chat request failed: {chat_response.status_code}")
            print(f"Response: {chat_response.text}")
            return False
        
        # Process the streaming response
        print("\nProcessing streaming response...")
        content_complete = ""
        
        for line in chat_response.iter_lines():
            if not line:
                continue
                
            try:
                # Decode and parse the JSON chunk
                chunk = json.loads(line.decode('utf-8'))
                
                # Extract type and content
                chunk_type = chunk.get('type')
                chunk_content = chunk.get('content', '')
                
                # Print chunk information
                if chunk_type == "connection_established":
                    print(f"Received chunk type: {chunk_type}")
                elif chunk_type == "system":
                    print(f"Received system message: {chunk.get('action')} - {chunk.get('status')}")
                    if chunk.get('content'):
                        print(f"System content: {chunk.get('content')[:100]}..." if len(chunk.get('content', '')) > 100 else chunk.get('content'))
                elif chunk_type == "content":
                    # Accumulate content for final display
                    content_complete += chunk_content
                    print(f"Received content chunk ({len(chunk_content)} chars)")
                else:
                    print(f"Received chunk type: {chunk_type}")
                    if chunk_content:
                        print(f"Content: {chunk_content[:100]}..." if len(chunk_content) > 100 else chunk_content)
                        
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                print(f"Raw line: {line.decode('utf-8')}")
                continue
                
        print("\n====== FINAL RESPONSE ======")
        print(content_complete)
        print("===========================")
        
        if content_complete:
            print("\n✓ Successfully received complete response from LLM Engine")
            return True
        else:
            print("\n❌ No content received in response")
            return False
            
    except Exception as e:
        print(f"❌ Error testing full chat flow: {e}")
        return False

if __name__ == "__main__":
    test_full_chat_flow()
