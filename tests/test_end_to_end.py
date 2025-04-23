#!/usr/bin/env python3
"""
End-to-End Test for RAI Chat Application
This script tests the entire flow from frontend to backend to LLM Engine and back.
"""

import requests
import json
import uuid
import time
import sys

# Configuration
BACKEND_URL = "http://localhost:6102"
TEST_MESSAGE = "What is RAI Chat and what features does it have?"

def test_end_to_end():
    """Test the entire flow from frontend to backend to LLM Engine and back"""
    print(f"Starting End-to-End test with message: '{TEST_MESSAGE}'")
    
    try:
        # Step 1: Check if the backend is healthy
        print("\n=== Step 1: Checking Backend Health ===")
        try:
            health_response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
            if health_response.status_code == 200:
                print("✅ Backend health check passed")
            else:
                print(f"❌ Backend health check failed: {health_response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Backend health check failed with exception: {str(e)}")
            return False
        
        # Step 2: Create a new session
        print("\n=== Step 2: Creating a New Session ===")
        session_id = str(uuid.uuid4())
        print(f"Generated session ID: {session_id}")
        
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
            
            if session_response.status_code == 200:
                session_result = session_response.json()
                print(f"✅ Session created successfully: {session_result.get('session_id')}")
            else:
                print(f"❌ Session creation failed: {session_response.status_code}")
                print(f"Response: {session_response.text}")
                return False
        except Exception as e:
            print(f"❌ Session creation failed with exception: {str(e)}")
            return False
        
        # Step 3: Send a message to the backend
        print("\n=== Step 3: Sending Message to Backend ===")
        message_payload = {
            "session_id": session_id,
            "message": TEST_MESSAGE
        }
        
        try:
            print(f"Sending message: '{TEST_MESSAGE}'")
            print(f"Using session ID: {session_id}")
            
            message_response = requests.post(
                f"{BACKEND_URL}/api/chat",
                json=message_payload,
                timeout=60  # Longer timeout for LLM processing
            )
            
            if message_response.status_code == 200:
                message_result = message_response.json()
                print("✅ Message sent successfully")
                print(f"Response status: {message_result.get('status', 'unknown')}")
            else:
                print(f"❌ Message sending failed: {message_response.status_code}")
                print(f"Response: {message_response.text}")
                return False
        except Exception as e:
            print(f"❌ Message sending failed with exception: {str(e)}")
            return False
        
        # Step 4: Verify the response content
        print("\n=== Step 4: Verifying Response Content ===")
        try:
            # Extract and print the response content
            response_text = message_result.get('response', '')
            if not response_text and 'content' in message_result:
                response_text = message_result.get('content', '')
            if not response_text and 'text' in message_result:
                response_text = message_result.get('text', '')
                
            print(f"\nResponse from LLM: {response_text[:200]}...")
            
            # Check if we got a meaningful response
            if len(response_text) > 50:
                print("✅ Received a valid response from the LLM")
            else:
                print("❌ Response too short or empty")
                return False
        except Exception as e:
            print(f"❌ Response verification failed with exception: {str(e)}")
            return False
        
        # Step 5: Verify the chat history
        print("\n=== Step 5: Verifying Chat History ===")
        try:
            history_response = requests.get(
                f"{BACKEND_URL}/api/sessions/{session_id}/history",
                timeout=10
            )
            
            if history_response.status_code == 200:
                history_result = history_response.json()
                messages = history_result.get('messages', [])
                print(f"✅ History retrieved successfully with {len(messages)} messages")
                
                if len(messages) >= 2:  # Should have at least the user message and the response
                    print("✅ Chat history contains the expected messages")
                else:
                    print(f"❌ Chat history doesn't contain enough messages: {len(messages)}")
                    return False
            else:
                print(f"❌ History retrieval failed: {history_response.status_code}")
                print(f"Response: {history_response.text}")
                return False
        except Exception as e:
            print(f"❌ History retrieval failed with exception: {str(e)}")
            return False
        
        # All steps passed
        return True
            
    except Exception as e:
        print(f"Error during end-to-end test: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== RAI Chat End-to-End Test ===")
    start_time = time.time()
    
    result = test_end_to_end()
    
    elapsed_time = time.time() - start_time
    print(f"\nTest completed in {elapsed_time:.2f} seconds")
    
    if result:
        print("\n✅ SUCCESS: End-to-End test passed! The entire RAI Chat system is working correctly.")
        exit(0)
    else:
        print("\n❌ FAILURE: End-to-End test failed. Please check the logs for more information.")
        exit(1)
