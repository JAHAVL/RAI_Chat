#!/usr/bin/env python3
# test_llm_direct.py - Test LLM Engine directly

import requests
import json
import sys
import os

# Configuration for Docker internal network
LLM_ENGINE_URL = "http://localhost:6101"  # Use localhost for testing from host machine

def test_llm_health():
    """Test the LLM engine health endpoint"""
    try:
        response = requests.get(f"{LLM_ENGINE_URL}/api/health", timeout=5)
        print(f"LLM Engine Health: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error connecting to LLM engine: {str(e)}")
        return False

def test_llm_completion():
    """Test the LLM completion endpoint directly"""
    try:
        # Create a simple message request - format based on the LLM Engine API
        request_data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, can you tell me what day it is today?"}
            ],
            "temperature": 0.7,
            "max_tokens": 300,
            "stream": False,
            "use_mock": False,  # Explicitly disable mock mode
            "engine": "gemini_default",  # Explicitly specify the engine
            "model": "gemini-1.5-flash-latest"  # Explicitly specify the model
        }
        
        print(f"Sending request to LLM Engine: {json.dumps(request_data, indent=2)}")
        
        # Send request to the correct chat completions endpoint
        response = requests.post(
            f"{LLM_ENGINE_URL}/api/chat/completions",
            json=request_data,
            timeout=30  # Longer timeout for LLM processing
        )
        
        print(f"LLM Completion Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("\nLLM Response:")
            print(json.dumps(response_data, indent=2))
            return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing LLM completion: {str(e)}")
        return False

def run_all_tests():
    """Run all LLM Engine tests"""
    print("=== Testing LLM Engine ===")
    
    # Test LLM engine health
    print("\n1. Testing LLM Engine Health...")
    if not test_llm_health():
        print("❌ LLM Engine health check failed")
        return False
    print("✅ LLM Engine health check passed")
    
    # Test LLM completion
    print("\n2. Testing LLM Completion...")
    if not test_llm_completion():
        print("❌ LLM Completion test failed")
        return False
    print("✅ LLM Completion test passed")
    
    print("\n=== All LLM Engine Tests Passed! ===")
    return True

if __name__ == "__main__":
    run_all_tests()
