#!/usr/bin/env python3
# test_backend_api.py - Test Backend API with LLM Engine

import requests
import json
import sys
import os

# Configuration for testing the Backend API
BACKEND_API_URL = "http://localhost:6100"  # Use localhost for testing from host

def test_backend_health():
    """Test the Backend API health endpoint"""
    try:
        response = requests.get(f"{BACKEND_API_URL}/api/health", timeout=5)
        print(f"Backend API Health: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error connecting to Backend API: {str(e)}")
        return False

def test_chat_api():
    """Test the Backend API chat endpoint"""
    try:
        # Create a simple chat message request
        request_data = {
            "message": "Hello, can you respond to this test message?",
            "stream": False
        }
        
        print(f"Sending request to Backend API: {json.dumps(request_data, indent=2)}")
        
        # Send request to chat endpoint
        response = requests.post(
            f"{BACKEND_API_URL}/api/chat",
            json=request_data,
            timeout=30  # Longer timeout for full processing chain
        )
        
        print(f"Backend API Chat Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("\nChat API Response:")
            print(json.dumps(response_data, indent=2))
            return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing chat API: {str(e)}")
        return False

def run_all_tests():
    """Run all Backend API tests"""
    print("=== Testing Backend API ===")
    
    # Test Backend API health
    print("\n1. Testing Backend API Health...")
    if not test_backend_health():
        print("❌ Backend API health check failed")
        return False
    print("✅ Backend API health check passed")
    
    # Test Chat API
    print("\n2. Testing Chat API with LLM Engine...")
    if not test_chat_api():
        print("❌ Chat API test failed")
        return False
    print("✅ Chat API test passed")
    
    print("\n=== All Backend API Tests Passed! ===")
    return True

if __name__ == "__main__":
    run_all_tests()
