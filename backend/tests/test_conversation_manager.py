#!/usr/bin/env python3
"""
Test script for the Backend Conversation Manager
This script tests the backend's ability to manage conversations and interact with the LLM Engine.
"""

import os
import sys
import json
import requests
import uuid
import time

print("Testing Backend Conversation Manager...")

# Backend API endpoint
BACKEND_URL = "http://localhost:5001"

def test_backend_health():
    """Test the Backend health endpoint"""
    try:
        response = requests.get(f"{BACKEND_URL}/health")
        if response.status_code == 200:
            print("✅ Backend health check passed")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend health check failed with exception: {str(e)}")
        return False

def test_create_session():
    """Test creating a new chat session"""
    try:
        # Create a unique session ID
        session_id = str(uuid.uuid4())
        
        payload = {
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/sessions", 
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Create session test passed")
            print(f"Session ID: {result.get('session_id', 'No session ID')}")
            return session_id
        else:
            print(f"❌ Create session test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Create session test failed with exception: {str(e)}")
        return None

def test_send_message(session_id):
    """Test sending a message to an existing session"""
    if not session_id:
        print("❌ Cannot test send_message without a valid session_id")
        return False
    
    try:
        payload = {
            "session_id": session_id,
            "message": "Hello, can you tell me about the RAI Chat application?"
        }
        
        print(f"Sending test message to backend: {payload['message']}")
        
        response = requests.post(
            f"{BACKEND_URL}/api/chat", 
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Send message test passed")
            print(f"Response: {result.get('response', 'No response')[:100]}...")
            return True
        else:
            print(f"❌ Send message test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Send message test failed with exception: {str(e)}")
        return False

def test_get_history(session_id):
    """Test retrieving chat history for a session"""
    if not session_id:
        print("❌ Cannot test get_history without a valid session_id")
        return False
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/sessions/{session_id}/history",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Get history test passed")
            print(f"History contains {len(result.get('messages', []))} messages")
            return True
        else:
            print(f"❌ Get history test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Get history test failed with exception: {str(e)}")
        return False

if __name__ == "__main__":
    # Run all tests
    health_result = test_backend_health()
    
    # Create a session for subsequent tests
    session_id = test_create_session()
    
    # Run tests that require a session
    if session_id:
        message_result = test_send_message(session_id)
        # Wait a moment for the message to be processed
        time.sleep(2)
        history_result = test_get_history(session_id)
    else:
        message_result = False
        history_result = False
    
    # Print summary
    print("\n=== Backend Conversation Manager Test Summary ===")
    print(f"Health Check: {'✅ Passed' if health_result else '❌ Failed'}")
    print(f"Create Session: {'✅ Passed' if session_id else '❌ Failed'}")
    print(f"Send Message: {'✅ Passed' if message_result else '❌ Failed'}")
    print(f"Get History: {'✅ Passed' if history_result else '❌ Failed'}")
    
    # Overall result
    if all([health_result, session_id, message_result, history_result]):
        print("\n✅ All Backend Conversation Manager tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some Backend Conversation Manager tests failed!")
        sys.exit(1)
