#!/usr/bin/env python
"""
Direct API test for memory functionality.
This test directly sends properly formatted tier requests and episodic searches to the API.
"""

import sys
import os
import json
import requests
import uuid
import time
import logging
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration
API_URL = "http://localhost:6102/api/chat"
HEADERS = {"Content-Type": "application/json"}

def send_request(endpoint, payload):
    """Send a request to the API endpoint."""
    try:
        response = requests.post(endpoint, json=payload, headers=HEADERS)
        return response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

def test_memory_directly():
    """Test memory functionality by directly sending formatted requests."""
    session_id = str(uuid.uuid4())
    logger.info(f"Created test session: {session_id}")
    
    # Step 1: Store a test message
    payload = {
        "message": "Remember that my favorite fruit is a dragon fruit",
        "session_id": session_id
    }
    
    response = send_request(API_URL, payload)
    logger.info(f"Stored test message, response: {response}")
    
    # Wait for processing
    time.sleep(2)
    
    # Step 2: Retrieve message ID (Use the database API endpoint)
    db_api_url = "http://localhost:6102/api/debug/messages"
    db_payload = {"session_id": session_id}
    
    messages = send_request(db_api_url, db_payload)
    if "error" in messages:
        logger.error(f"Failed to retrieve messages: {messages['error']}")
        return False
    
    # Find the message ID of our test message
    message_id = None
    for msg in messages:
        if "favorite fruit" in msg.get("content", ""):
            message_id = msg.get("message_id")
            break
    
    if not message_id:
        logger.error("Failed to find test message ID")
        return False
    
    logger.info(f"Found test message ID: {message_id}")
    
    # Step 3: Send direct tier request
    tier_request_payload = {
        "message": f"Question: What's my favorite fruit? [REQUEST_TIER:3:{message_id}]",
        "session_id": session_id
    }
    
    logger.info(f"Sending tier request: {tier_request_payload}")
    tier_response = send_request(API_URL, tier_request_payload)
    logger.info(f"Tier request response: {tier_response}")
    
    # Wait for processing
    time.sleep(3)
    
    # Step 4: Send direct episodic search
    episodic_search_payload = {
        "message": "[SEARCH_EPISODIC:favorite fruit]",
        "session_id": session_id
    }
    
    logger.info(f"Sending episodic search: {episodic_search_payload}")
    search_response = send_request(API_URL, episodic_search_payload)
    logger.info(f"Episodic search response: {search_response}")
    
    # Step 5: Check the database to see if tier was properly updated
    updated_messages = send_request(db_api_url, db_payload)
    
    if "error" in updated_messages:
        logger.error(f"Failed to retrieve updated messages: {updated_messages['error']}")
        return False
    
    # Find our message and check its tier
    tier_updated = False
    for msg in updated_messages:
        if msg.get("message_id") == message_id:
            tier_level = msg.get("required_tier_level")
            logger.info(f"Message tier level after request: {tier_level}")
            tier_updated = tier_level == 3
            break
    
    if tier_updated:
        logger.info("✅ SUCCESS: Tier level was properly updated")
    else:
        logger.error("❌ FAILURE: Tier level was not updated")
    
    # Return results
    return {
        "tier_request_successful": tier_updated,
        "test_passed": tier_updated
    }

if __name__ == "__main__":
    logger.info("Starting direct memory API test...")
    result = test_memory_directly()
    if isinstance(result, dict):
        logger.info(f"Test result: {result}")
        sys.exit(0 if result.get("test_passed") else 1)
    else:
        logger.info(f"Test result: {result}")
        sys.exit(0 if result else 1)
