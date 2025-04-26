#!/usr/bin/env python3
"""
Contextual Memory Long-Term Coherence Test

This test script verifies whether the RAI Chat application maintains contextual
memory across a multi-turn conversation by sending a series of related messages
and analyzing responses for evidence of memory retention.
"""

import requests
import json
import time
import re
import sys
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:6102"
TEST_USER_ID = 123
TEST_USERNAME = "testuser123"

# Auth headers to use for all requests
AUTH_HEADERS = {
    "Content-Type": "application/json",
    "X-Test-User-ID": str(TEST_USER_ID),
    "X-Test-Username": TEST_USERNAME
}

# Test conversation flow - designed to test memory and coherence
TEST_CONVERSATION = [
    # Initial message to establish context
    "My name is Jordan and I'm working on a project called RAI Chat.",
    
    # Establishing personal details
    "I live in New York and I enjoy hiking on weekends.",
    
    # First direct question requiring memory of the name
    "What's my name? And what project am I working on?",
    
    # Adding more context
    "The RAI Chat project uses Flask for the backend and React for the frontend.",
    
    # Question requiring memory of multiple facts
    "Where do I live, and what activity do I enjoy on weekends?",
    
    # Technical question requiring memory of the project details
    "What technologies does my project use?",
    
    # Adding new information
    "I started this project in January 2025 and I want to finish it by December 2025.",
    
    # Complex follow-up requiring integration of multiple context items
    "Based on what you know about me, my project, and my timeline, what do you think my biggest challenges will be?",
    
    # Final test requiring deep contextual memory
    "Summarize everything you know about me and my project so far."
]

# Expected memory items that should be retained
MEMORY_MARKERS = {
    "name": ["Jordan", "jordan"],
    "project": ["RAI Chat", "RAI"],
    "location": ["New York", "new york", "NY"],
    "hobby": ["hiking", "hike"],
    "backend": ["Flask", "flask"],
    "frontend": ["React", "react"],
    "timeline": ["January 2025", "jan 2025", "2025", "December", "dec 2025"]
}

def create_session():
    """Create a new test session"""
    session_payload = {
        "title": f"Contextual Memory Test {datetime.now().strftime('%Y%m%d-%H%M%S')}"
    }
    
    try:
        session_response = requests.post(
            f"{BACKEND_URL}/api/sessions/create",
            headers=AUTH_HEADERS,
            json=session_payload,
            timeout=10
        )
        
        if session_response.status_code != 200:
            print(f"\u274c Failed to create session: {session_response.status_code}")
            print(f"Response: {session_response.text}")
            return None
        
        session_data = session_response.json()
        session_id = session_data.get("session_id")
        
        if not session_id:
            print("\u274c No session ID returned")
            return None
            
        print(f"\u2713 Session created successfully with ID: {session_id}")
        return session_id
        
    except Exception as e:
        print(f"\u274c Error creating session: {e}")
        return None

def send_message(session_id, message, turn_number):
    """Send a message in the conversation and return the response"""
    print(f"\n=== Turn {turn_number}: Sending message ===")
    print(f"Message: '{message}'")
    
    chat_payload = {
        "message": message,
        "session_id": session_id
    }
    
    try:
        # Send the chat request with stream=True to get a streaming response
        chat_response = requests.post(
            f"{BACKEND_URL}/api/chat",
            headers=AUTH_HEADERS,
            json=chat_payload,
            stream=True,
            timeout=60
        )
        
        if chat_response.status_code != 200:
            print(f"\u274c Chat request failed: {chat_response.status_code}")
            print(f"Response: {chat_response.text}")
            return None
        
        # Process the streaming response
        print("Processing response...")
        content_complete = ""
        
        for line in chat_response.iter_lines():
            if not line:
                continue
                
            try:
                # Decode and parse the JSON chunk
                chunk = json.loads(line.decode('utf-8'))
                
                # Extract type and content
                chunk_type = chunk.get('type')
                chunk_content = chunk.get('content', '')
                
                if chunk_type == "content" and chunk_content:
                    content_complete += chunk_content
                    
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                continue
        
        # Clean up any JSON formatting in the response
        clean_response = clean_llm_response(content_complete)
        
        print(f"\nResponse received ({len(clean_response)} chars):")
        print(f"{clean_response[:150]}..." if len(clean_response) > 150 else clean_response)
        return clean_response
            
    except Exception as e:
        print(f"\u274c Error sending message: {e}")
        return None

def clean_llm_response(response):
    """Clean up LLM response by removing JSON formatting if present"""
    
    # If the response is a JSON string or contains markdown JSON blocks, extract the actual content
    if response.strip().startswith('```json'):
        # Extract from markdown code block
        try:
            match = re.search(r'```json\s*\n(.+?)\n\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        # Try to extract from tier3 in response_tiers
                        if 'llm_response' in parsed and 'response_tiers' in parsed['llm_response']:
                            return parsed['llm_response']['response_tiers'].get('tier3', response)
                        else:
                            # Return the most likely human-readable content
                            for key in ['response', 'content', 'message', 'text']:
                                if key in parsed:
                                    return parsed[key]
                except:
                    pass  # If we can't parse as JSON, return the original string
        except:
            pass  # If regex fails, return the original string
    elif response.strip().startswith('{'):
        # Try to parse as raw JSON
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                # Try to extract from tier3 in response_tiers
                if 'llm_response' in parsed and 'response_tiers' in parsed['llm_response']:
                    return parsed['llm_response']['response_tiers'].get('tier3', response)
                else:
                    # Return the most likely human-readable content
                    for key in ['response', 'content', 'message', 'text']:
                        if key in parsed:
                            return parsed[key]
        except:
            pass  # If we can't parse as JSON, return the original string
            
    return response

def analyze_memory_retention(responses):
    """Analyze responses for evidence of memory retention"""
    print("\n===== MEMORY RETENTION ANALYSIS =====\n")
    
    memory_scores = {category: 0 for category in MEMORY_MARKERS.keys()}
    total_possible = 0
    
    # Analyze each response against expected memory markers
    for i, response in enumerate(responses):
        if i < 2:  # Skip the first two turns - they're just providing info
            continue
            
        turn_number = i + 1
        print(f"Turn {turn_number} Analysis:")
        
        # Check for each memory category
        for category, markers in MEMORY_MARKERS.items():
            found = False
            for marker in markers:
                if marker.lower() in response.lower():
                    found = True
                    memory_scores[category] += 1
                    break
            
            # After turn 2, all categories should be checkable
            if i >= 2:
                total_possible += 1
                if found:
                    print(f"  \u2713 Remembered '{category}'")
                else:
                    print(f"  \u274c Failed to remember '{category}'")
    
    # Calculate overall score
    total_remembered = sum(memory_scores.values())
    memory_percentage = (total_remembered / total_possible * 100) if total_possible > 0 else 0
    
    print(f"\nOverall Memory Retention: {total_remembered}/{total_possible} ({memory_percentage:.1f}%)")
    
    # Detailed breakdown by category
    print("\nCategory Breakdown:")
    for category, score in memory_scores.items():
        possible = len(responses) - 2  # All responses after the first two
        percentage = (score / possible * 100) if possible > 0 else 0
        print(f"  {category}: {score}/{possible} ({percentage:.1f}%)")
    
    # Overall assessment
    if memory_percentage >= 80:
        print("\n\u2713 EXCELLENT: Contextual memory system is working very well!")
    elif memory_percentage >= 60:
        print("\n\u2713 GOOD: Contextual memory system is working adequately.")
    elif memory_percentage >= 40:
        print("\n\u26a0 FAIR: Contextual memory system is functioning but needs improvement.")
    else:
        print("\n\u274c POOR: Contextual memory system is not retaining information effectively.")

def run_memory_test():
    """Run the full contextual memory test"""
    print("\n***** CONTEXTUAL MEMORY COHERENCE TEST *****\n")
    
    # Create a session
    session_id = create_session()
    if not session_id:
        return
    
    # Run through the test conversation
    responses = []
    for i, message in enumerate(TEST_CONVERSATION):
        turn_number = i + 1
        response = send_message(session_id, message, turn_number)
        
        if not response:
            print(f"\u274c Failed to get response for turn {turn_number}. Aborting test.")
            return
            
        responses.append(response)
        
        # Small delay between messages to simulate realistic conversation
        if i < len(TEST_CONVERSATION) - 1:
            time.sleep(1)
    
    # Analyze how well the system retained information
    analyze_memory_retention(responses)

if __name__ == "__main__":
    run_memory_test()
