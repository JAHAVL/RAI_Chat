#!/usr/bin/env python
"""
End-to-end test for the RAI Chat API
This script tests the full system by sending real requests to the backend API
"""

import requests
import json
import time
import sys
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API configuration
API_URL = "http://localhost:6102"
CHAT_ENDPOINT = "/api/chat"  # Update the endpoint path to match the blueprint
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test_token"  # Will be replaced by auto-auth in dev mode
}

def test_chat_api():
    """Send a series of messages to test tier upgrades and memory functionality"""
    # Create a unique session ID for this test
    session_id = str(uuid.uuid4())
    logger.info(f"Starting chat API test with session ID: {session_id}")
    
    # Test messages that will trigger tier upgrades and memory usage
    test_messages = [
        "Hi, my name is Jordan and I'm testing the memory system.",
        "My favorite color is blue. Remember that for later.",
        "What's the weather like today in San Francisco?",
        "Let's talk about Python programming. It's a versatile language used for web development, data science, and more.",
        "By the way, I live in California and I work as a software engineer.",
        "What did I say my name was earlier?",  # Should trigger tier 2/3 request
        "What's my favorite color?",  # Should trigger tier 2/3 request
        "Where do I live?",  # Should trigger tier 2/3 request
    ]
    
    # Keep track of all messages to check for tier requests
    all_responses = []
    
    try:
        for i, message in enumerate(test_messages):
            logger.info(f"Sending message {i+1}/{len(test_messages)}: {message[:30]}...")
            
            # Send the message to the API
            response = requests.post(
                f"{API_URL}{CHAT_ENDPOINT}",
                headers=HEADERS,
                json={
                    "message": message,
                    "session_id": session_id
                }
            )
            
            # Check if request was successful
            response.raise_for_status()
            
            # Get the response data
            data = response.json()
            all_responses.append(data)
            
            logger.info(f"Response: {data.get('assistant_message', '')[:50]}...")
            
            # Small delay to avoid overwhelming the server
            time.sleep(1)
        
        # Analyze the responses for tier requests
        tier_requests_found = 0
        for response in all_responses:
            if response.get('has_tier_request', False):
                tier_requests_found += 1
        
        # Check if memory is working correctly
        memory_working = tier_requests_found > 0
        
        if memory_working:
            logger.info(f"✅ Success! Found {tier_requests_found} tier upgrade requests")
            logger.info("The memory system is working correctly")
            return True
        else:
            logger.error("❌ Test failed! No tier requests were found in the responses")
            logger.error("The memory system is not working correctly")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_chat_api()
    sys.exit(0 if success else 1)
