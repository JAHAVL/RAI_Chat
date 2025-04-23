#!/usr/bin/env python3
"""
Docker frontend test script
This script will be copied into the frontend Docker container to test communication with the backend
"""

import requests
import json
import sys
import uuid

def test_backend_health():
    """Test the Backend health endpoint from inside the frontend container"""
    print("Testing Backend health from frontend container...")
    try:
        response = requests.get("http://backend:6102/api/health", timeout=5)
        print(f"Backend health check: {response.status_code}")
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
    """Test creating a session via the backend API"""
    print("Testing session creation...")
    try:
        session_id = str(uuid.uuid4())
        payload = {
            "session_id": session_id,
            "user_id": "test_user"
        }
        
        response = requests.post(
            "http://backend:6102/api/sessions",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Create session test passed")
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
    """Test sending a message to the backend API"""
    if not session_id:
        print("❌ Cannot test send_message without a valid session_id")
        return False
    
    print("Testing sending a message...")
    try:
        payload = {
            "session_id": session_id,
            "message": "Hello, can you tell me about the RAI Chat application?"
        }
        
        response = requests.post(
            "http://backend:6102/api/chat",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Send message test passed")
            print(f"Response: {result.get('response', 'No response')[:100]}...")
            return True
        else:
            print(f"❌ Send message test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Send message test failed with exception: {str(e)}")
        return False

def main():
    """Run all tests"""
    backend_health = test_backend_health()
    session_id = test_create_session() if backend_health else None
    message_test = test_send_message(session_id) if session_id else False
    
    print("\n=== Test Summary ===")
    print(f"Backend Health: {'✅ Passed' if backend_health else '❌ Failed'}")
    print(f"Create Session: {'✅ Passed' if session_id else '❌ Failed'}")
    print(f"Send Message: {'✅ Passed' if message_test else '❌ Failed'}")
    
    if backend_health and session_id and message_test:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
