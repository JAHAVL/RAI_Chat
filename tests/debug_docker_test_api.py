#!/usr/bin/env python3
# debug_docker_test_api.py - Debug test script for API connectivity from within Docker

import requests
import json
import time
import sys
import os

# Configuration for Docker internal network
BACKEND_URL = "http://backend:6102"
LLM_ENGINE_URL = "http://llm-engine:6101"

def test_backend_health():
    """Test the backend health endpoint"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        print(f"Backend Health: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error connecting to backend: {str(e)}")
        return False

def test_llm_engine_health():
    """Test the LLM engine health endpoint"""
    try:
        response = requests.get(f"{LLM_ENGINE_URL}/api/health", timeout=5)
        print(f"LLM Engine Health: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error connecting to LLM engine: {str(e)}")
        return False

def test_create_session():
    """Test creating a new chat session"""
    try:
        # In RAI Chat, sessions are created by sending a message with sessionId='new_chat'
        response = requests.post(
            f"{BACKEND_URL}/api/chat", 
            json={
                "session_id": "new_chat",
                "message": "Create new chat: Test Session"
            },
            timeout=10
        )
        print(f"Create Session: {response.status_code}")
        print(f"Raw Response Content: {response.content}")
        print(f"Response Headers: {response.headers}")
        
        # Try to parse the response as JSON if possible
        try:
            session_data = response.json()
            print(f"Session created: {session_data}")
            return session_data.get("session_id")
        except Exception as e:
            print(f"Error parsing response as JSON: {str(e)}")
            return None
    except Exception as e:
        print(f"Error creating session: {str(e)}")
        return None

def run_all_tests():
    """Run all connectivity tests"""
    print("=== Testing API Connectivity (Docker Internal Network) ===")
    
    # Test backend health
    print("\n1. Testing Backend Health...")
    if not test_backend_health():
        print("❌ Backend health check failed")
        return False
    print("✅ Backend health check passed")
    
    # Test LLM engine health
    print("\n2. Testing LLM Engine Health...")
    if not test_llm_engine_health():
        print("❌ LLM Engine health check failed")
        return False
    print("✅ LLM Engine health check passed")
    
    # Test session creation
    print("\n3. Testing Session Creation...")
    session_id = test_create_session()
    if not session_id:
        print("❌ Session creation failed")
        return False
    print(f"✅ Session creation passed, session_id: {session_id}")
    
    print("\n=== All Tests Passed! ===")
    return True

if __name__ == "__main__":
    run_all_tests()
