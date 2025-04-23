#!/usr/bin/env python3
"""
Direct LLM response test
This script tests the LLM Engine's ability to generate a proper response.
"""

import requests
import json
import time
import sys

# Configuration
LLM_ENGINE_URL = "http://localhost:6101"
TEST_PROMPT = "Hello, can you tell me about yourself? What is RAI Chat?"

def test_llm_direct_response():
    """Test the LLM Engine's ability to generate a proper response"""
    print(f"Testing LLM response with prompt: '{TEST_PROMPT}'")
    
    try:
        # First check if the LLM Engine is healthy
        health_response = requests.get(f"{LLM_ENGINE_URL}/api/health", timeout=5)
        if health_response.status_code != 200:
            print(f"❌ LLM Engine health check failed: {health_response.status_code}")
            return False
            
        print("✅ LLM Engine health check passed")
        
        # Now send a direct request to the LLM Engine
        payload = {
            "prompt": TEST_PROMPT,
            "max_tokens": 500,  # Request a longer response
            "temperature": 0.7,
            "model": "gemini-1.5-flash-latest"  # Specify the model explicitly
        }
        
        print("Sending request to LLM Engine...")
        start_time = time.time()
        
        response = requests.post(
            f"{LLM_ENGINE_URL}/api/generate",
            json=payload,
            timeout=60  # Longer timeout for LLM processing
        )
        
        elapsed_time = time.time() - start_time
        print(f"Request completed in {elapsed_time:.2f} seconds")
        
        if response.status_code != 200:
            print(f"❌ LLM Engine response failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        # Parse and display the response
        result = response.json()
        print("\n=== LLM Response ===")
        print(f"Raw response: {json.dumps(result, indent=2)}")
        
        # Extract and print the response content
        response_text = result.get('response', '')
        if not response_text and 'content' in result:
            response_text = result.get('content', '')
        if not response_text and 'text' in result:
            response_text = result.get('text', '')
        if not response_text and 'generated_text' in result:
            response_text = result.get('generated_text', '')
            
        print(f"\nExtracted Response: {response_text}")
        
        # Check if we got a meaningful response
        if len(response_text) > 50:
            print("\n✅ SUCCESS: Received a valid response from the LLM")
            return True
        else:
            print("\n❌ FAILURE: Response too short or empty")
            return False
            
    except Exception as e:
        print(f"Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    result = test_llm_direct_response()
    if result:
        print("\nTest completed successfully! The LLM Engine is generating proper responses.")
        exit(0)
    else:
        print("\nTest failed. Please check the logs for more information.")
        exit(1)
