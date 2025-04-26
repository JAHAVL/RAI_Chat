#!/usr/bin/env python
"""
End-to-end memory recall test for RAI Chat
"""

import sys
import os
import json
import requests
import uuid
import time
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration
API_URL = "http://localhost:6102/api/chat"
HEADERS = {
    "Content-Type": "application/json",
}

def create_session():
    """Create a new session ID"""
    return str(uuid.uuid4())

def parse_response(response_text):
    """Parse the streaming response and extract the JSON content"""
    response_lines = response_text.strip().split('\n')
    last_line = response_lines[-1]
    
    try:
        # Sometimes the response contains escaped JSON
        response_data = json.loads(last_line)
        return response_data
    except json.JSONDecodeError:
        logger.error(f"Failed to parse response: {last_line}")
        return None

def send_message(message, session_id):
    """
    Send a message to the API and return the parsed response
    """
    payload = {
        "message": message,
        "session_id": session_id
    }
    
    response = requests.post(API_URL, json=payload, headers=HEADERS)
    if response.status_code != 200:
        logger.error(f"API request failed with status {response.status_code}: {response.text}")
        return None
    
    return parse_response(response.text)

def extract_tier_requests(response_data):
    """Extract tier requests from the response data"""
    if not response_data or "content" not in response_data:
        return []
    
    content = response_data["content"]
    # Pattern to match [REQUEST_TIER:level:message_id]
    pattern = r"\[REQUEST_TIER:(\d+):([^\]]+)\]"
    return re.findall(pattern, content)

def extract_episodic_requests(response_data):
    """Extract episodic search requests from the response data"""
    if not response_data or "content" not in response_data:
        return []
    
    content = response_data["content"]
    # Pattern to match [SEARCH_EPISODIC:query]
    pattern = r"\[SEARCH_EPISODIC:([^\]]+)\]"
    return re.findall(pattern, content)

def get_response_text(response_data):
    """Extract the text content from a response"""
    if not response_data:
        return ""
    
    if "content" in response_data:
        content = response_data["content"]
        # Remove any tier or episodic request markers
        content = re.sub(r"\[REQUEST_TIER:[^\]]+\]", "", content)
        content = re.sub(r"\[SEARCH_EPISODIC:[^\]]+\]", "", content)
        return content
    
    return ""

def get_message_with_followup(message, session_id, max_follow_ups=2):
    """
    Send a message and follow up with tier requests or episodic searches as needed
    
    This simulates what the full frontend/backend interaction would do to process
    tier upgrade requests and episodic search requests.
    """
    logger.info(f"Sending initial message: {message}")
    response_data = send_message(message, session_id)
    
    if not response_data:
        return ""
    
    # Get the initial response text
    response_text = get_response_text(response_data)
    
    # Extract any tier or episodic requests
    tier_requests = extract_tier_requests(response_data)
    episodic_requests = extract_episodic_requests(response_data)
    
    # Track follow-up count to prevent infinite loops
    follow_up_count = 0
    
    # Follow up on tier or episodic requests
    while (tier_requests or episodic_requests) and follow_up_count < max_follow_ups:
        follow_up_count += 1
        
        # Generate a follow-up message based on the requests
        if tier_requests:
            tier_level, message_id = tier_requests[0]  # Just use the first one
            follow_up = f"Please provide more details about that. (simulating tier {tier_level} upgrade)"
            logger.info(f"Following up with tier request: {follow_up}")
        elif episodic_requests:
            query = episodic_requests[0]  # Just use the first one
            follow_up = f"Let me search my memories for '{query}'. (simulating episodic search)"
            logger.info(f"Following up with episodic search: {follow_up}")
        
        # Send the follow-up message
        follow_up_response = send_message(follow_up, session_id)
        
        if not follow_up_response:
            break
        
        # Update the response text
        follow_up_text = get_response_text(follow_up_response)
        response_text += f"\n{follow_up_text}"
        
        # Check for new requests
        tier_requests = extract_tier_requests(follow_up_response)
        episodic_requests = extract_episodic_requests(follow_up_response)
        
        # Add a short delay to avoid rate limiting
        time.sleep(1)
    
    return response_text

def run_memory_test():
    """
    Run a memory test by introducing facts and then asking about them
    """
    # Create a new session
    session_id = create_session()
    logger.info(f"Created new session: {session_id}")
    
    # Facts to introduce
    facts = [
        ("favorite color", "cerulean blue"),
        ("hometown", "Springfield, Illinois"),
        ("birthday", "March 15"),
        ("pet", "a golden retriever named Max"),
        ("hobby", "collecting vintage postcards"),
        ("dream job", "wildlife photographer in national parks"),
        ("favorite book", "The Count of Monte Cristo"),
        ("favorite movie", "The Shawshank Redemption"),
        ("favorite food", "spicy Thai curry"),
        ("college major", "environmental science")
    ]
    
    # Step 1: Introduce facts
    logger.info("=== Introducing Facts ===")
    for i, (fact_key, fact_value) in enumerate(facts):
        message = f"Let me tell you about my {fact_key}. It's {fact_value}."
        logger.info(f"Sending fact {i+1}/{len(facts)}: {message}")
        
        response_data = send_message(message, session_id)
        response_text = get_response_text(response_data) if response_data else ""
        logger.info(f"Response received: {response_text[:100]}...")
        
        # Add a short delay between messages to avoid rate limiting
        time.sleep(1)
    
    # Add some conversation turns to push facts out of immediate context
    filler_messages = [
        "How's the weather today?",
        "Tell me an interesting fact about space.",
        "What's your favorite season?",
        "If you could travel anywhere, where would you go?",
        "Tell me about advances in renewable energy."
    ]
    
    logger.info("=== Adding filler conversation ===")
    for i, message in enumerate(filler_messages):
        logger.info(f"Sending filler {i+1}/{len(filler_messages)}: {message}")
        send_message(message, session_id)
        time.sleep(1)
    
    # Step 2: Quiz about facts with follow-ups for tier/episodic requests
    logger.info("=== Testing Memory Recall with Follow-ups ===")
    successful_recalls = 0
    
    for fact_key, fact_value in facts:
        quiz_message = f"What is my {fact_key}?"
        logger.info(f"Asking about {fact_key}: {quiz_message}")
        
        # Get response with follow-ups for tier/episodic requests
        response = get_message_with_followup(quiz_message, session_id)
        logger.info(f"Final response: {response}")
        
        # Check if the response contains the fact value
        if fact_value.lower() in response.lower():
            logger.info(f"✅ SUCCESS: Correctly recalled {fact_key}")
            successful_recalls += 1
        else:
            logger.error(f"❌ FAILURE: Failed to recall {fact_key}")
        
        # Add a short delay between quiz questions
        time.sleep(1)
    
    # Calculate and report accuracy
    accuracy = (successful_recalls / len(facts)) * 100
    logger.info(f"Memory recall accuracy: {accuracy:.2f}% ({successful_recalls}/{len(facts)})")
    
    return accuracy

if __name__ == "__main__":
    logger.info("Starting memory recall test...")
    accuracy = run_memory_test()
    
    # Exit with 0 if accuracy is above 90%, 1 otherwise
    if accuracy >= 90:
        logger.info("Test PASSED: Accuracy above 90%")
        sys.exit(0)
    else:
        logger.error("Test FAILED: Accuracy below 90%")
        sys.exit(1)
