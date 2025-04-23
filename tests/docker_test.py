#!/usr/bin/env python3
"""
Docker container test script
This script will be copied into the Docker container to test internal communication
"""

import requests
import json
import sys

def test_llm_engine():
    """Test the LLM Engine from inside the backend container"""
    print("Testing LLM Engine from backend container...")
    try:
        response = requests.get("http://llm-engine:6101/api/health", timeout=5)
        print(f"LLM Engine health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ LLM Engine health check passed")
            return True
        else:
            print(f"❌ LLM Engine health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ LLM Engine health check failed with exception: {str(e)}")
        return False

def test_llm_generate():
    """Test generating text with the LLM Engine"""
    print("Testing LLM generate endpoint...")
    try:
        payload = {
            "prompt": "Hello, can you tell me about the RAI Chat application?",
            "max_tokens": 100,
            "temperature": 0.7
        }
        
        response = requests.post(
            "http://llm-engine:6101/api/generate", 
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ LLM generate test passed")
            print(f"Response: {result.get('response', 'No response')[:100]}...")
            return True
        else:
            print(f"❌ LLM generate test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ LLM generate test failed with exception: {str(e)}")
        return False

def main():
    """Run all tests"""
    llm_health = test_llm_engine()
    llm_generate = test_llm_generate()
    
    print("\n=== Test Summary ===")
    print(f"LLM Engine Health: {'✅ Passed' if llm_health else '❌ Failed'}")
    print(f"LLM Generate: {'✅ Passed' if llm_generate else '❌ Failed'}")
    
    if llm_health and llm_generate:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
