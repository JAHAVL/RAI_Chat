#!/usr/bin/env python3
# stream_docker_test_api.py - Test script for API connectivity with streaming support

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
    """Test creating a new chat session with streaming support"""
    try:
        # In RAI Chat, sessions are created by sending a message with sessionId='new_chat'
        response = requests.post(
            f"{BACKEND_URL}/api/chat", 
            json={
                "session_id": "new_chat",
                "message": "Create new chat: Test Session"
            },
            stream=True,  # Enable streaming
            timeout=10
        )
        print(f"Create Session: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        
        # Process the streaming response
        session_id = None
        last_chunk = None
        
        for line in response.iter_lines():
            if line:
                print(f"Stream chunk: {line.decode('utf-8')}")
                try:
                    chunk_data = json.loads(line.decode('utf-8'))
                    last_chunk = chunk_data
                    if 'session_id' in chunk_data:
                        session_id = chunk_data['session_id']
                except Exception as e:
                    print(f"Error parsing chunk: {str(e)}")
        
        if last_chunk:
            print(f"Final chunk: {last_chunk}")
            
        return session_id
    except Exception as e:
        print(f"Error creating session: {str(e)}")
        return None

def test_send_message(session_id, message="Hello, how are you?"):
    """Test sending a message to the chat API with streaming support"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat",
            json={
                "session_id": session_id,
                "message": message
            },
            stream=True,  # Enable streaming
            timeout=30  # Longer timeout for message processing
        )
        print(f"Send Message: {response.status_code}")
        
        # Process the streaming response
        last_chunk = None
        
        for line in response.iter_lines():
            if line:
                print(f"Stream chunk: {line.decode('utf-8')}")
                try:
                    chunk_data = json.loads(line.decode('utf-8'))
                    last_chunk = chunk_data
                except Exception as e:
                    print(f"Error parsing chunk: {str(e)}")
        
        if last_chunk:
            print(f"Final chunk: {last_chunk}")
            return True
        else:
            return False
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return False

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
    
    # Test sending a message
    print("\n4. Testing Message Sending...")
    if not test_send_message(session_id):
        print("❌ Message sending failed")
        return False
    print("✅ Message sending passed")
    
    print("\n=== All Tests Passed! ===")
    return True

if __name__ == "__main__":
    run_all_tests()
