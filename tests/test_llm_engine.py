#!/usr/bin/env python3
"""
Test script for the LLM Engine
This script directly tests the LLM Engine's ability to generate responses.
"""

import os
import sys
import json
import requests
import time

# Add the current directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Testing LLM Engine...")

# LLM Engine endpoint
LLM_ENGINE_URL = "http://localhost:6101"

def test_llm_engine_health():
    """Test the LLM Engine health endpoint"""
    try:
        response = requests.get(f"{LLM_ENGINE_URL}/api/health")
        if response.status_code == 200:
            print("✅ LLM Engine health check passed")
            return True
        else:
            print(f"❌ LLM Engine health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ LLM Engine health check failed with exception: {str(e)}")
        return False

def test_llm_engine_generate():
    """Test the LLM Engine generate endpoint"""
    try:
        payload = {
            "prompt": "Hello, can you tell me about the RAI Chat application?",
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        print(f"Sending test prompt to LLM Engine: {payload['prompt']}")
        
        response = requests.post(
            f"{LLM_ENGINE_URL}/api/generate", 
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ LLM Engine generate test passed")
            print(f"Response: {result.get('response', 'No response')[:100]}...")
            return True
        else:
            print(f"❌ LLM Engine generate test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ LLM Engine generate test failed with exception: {str(e)}")
        return False

def test_llm_engine_models():
    """Test the LLM Engine models endpoint"""
    try:
        response = requests.get(f"{LLM_ENGINE_URL}/api/models")
        if response.status_code == 200:
            models = response.json()
            print(f"✅ LLM Engine models test passed")
            print(f"Available models: {models}")
            return True
        else:
            print(f"❌ LLM Engine models test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ LLM Engine models test failed with exception: {str(e)}")
        return False

if __name__ == "__main__":
    # Run all tests
    health_result = test_llm_engine_health()
    models_result = test_llm_engine_models()
    generate_result = test_llm_engine_generate()
    
    # Print summary
    print("\n=== LLM Engine Test Summary ===")
    print(f"Health Check: {'✅ Passed' if health_result else '❌ Failed'}")
    print(f"Models Check: {'✅ Passed' if models_result else '❌ Failed'}")
    print(f"Generate Test: {'✅ Passed' if generate_result else '❌ Failed'}")
    
    # Overall result
    if all([health_result, models_result, generate_result]):
        print("\n✅ All LLM Engine tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some LLM Engine tests failed!")
        sys.exit(1)
