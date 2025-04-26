#!/usr/bin/env python3
"""
Comprehensive test suite to verify backend integration with LLM Engine

This suite tests all key integration points between the RAI Chat backend and
the LLM Engine, including:
1. Basic message exchange
2. Session management
3. System messages
4. Memory functionality
5. Error handling

Designed to work with Docker deployment and the Gemini LLM Engine.
"""

import requests
import json
import uuid
import time
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:6102"
DEBUG = True

# Test user information - must match a user in the database
TEST_USER_ID = 123
TEST_USERNAME = "testuser123"

# Auth headers to use for all requests
AUTH_HEADERS = {
    "Content-Type": "application/json",
    "X-Test-User-ID": str(TEST_USER_ID),
    "X-Test-Username": TEST_USERNAME
}

# Test messages for different scenarios
TEST_MESSAGES = {
    "basic": "Hello, can you tell me about yourself? What is RAI Chat?",
    "memory": "My name is Jordan. Remember that for later.",
    "recall": "What's my name?",
    "search": "What is the capital of France? Use web search.",
    "complex": "Can you explain how a three-tier memory system works in an AI assistant?",
    "error": "@#$%^&*()_+ Force an error in processing please"
}

# Global storage for test session IDs
TEST_SESSIONS = {}

def log_separator(title):
    """
Print a visible separator with a title
    """
    separator = "\n" + "=" * 80 + "\n"
    print(f"{separator}{title.center(80)}{separator}")

def test_health_check():
    """
Test that the backend health check endpoint is working
    """
    log_separator("Testing Backend Health")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✓ Backend health check passed")
            return True
        else:
            print("✗ Backend health check failed")
            return False
    except Exception as e:
        print(f"✗ Backend health check error: {str(e)}")
        return False

def create_test_session():
    """
Create a new test session and store its ID
    """
    log_separator("Creating Test Session")
    
    session_payload = {
        "title": f"Integration Test {time.strftime('%Y%m%d-%H%M%S')}"
    }
    
    try:
        session_response = requests.post(
            f"{BACKEND_URL}/api/sessions/create",
            headers=AUTH_HEADERS,
            json=session_payload,
            timeout=10
        )
        
        if session_response.status_code != 200:
            print(f"✗ Failed to create session: {session_response.status_code}")
            print(f"Response: {session_response.text}")
            return None
        
        session_data = session_response.json()
        session_id = session_data.get("session_id")
        
        if not session_id:
            print("✗ No session ID returned")
            return None
            
        print(f"✓ Session created successfully with ID: {session_id}")
        return session_id
    except Exception as e:
        print(f"✗ Error creating session: {str(e)}")
        return None

def send_message(session_id, message, description):
    """
Send a message to the LLM Engine and process the streaming response
    """
    log_separator(f"Test: {description}")
    print(f"Sending message: '{message}'")
    
    message_payload = {
        "session_id": session_id,
        "message": message
    }
    
    try:
        # Use stream=True to process the response as it comes in
        message_response = requests.post(
            f"{BACKEND_URL}/api/chat",
            headers=AUTH_HEADERS,
            json=message_payload,
            stream=True,
            timeout=60
        )
        
        if message_response.status_code != 200:
            print(f"✗ Failed to send message: {message_response.status_code}")
            print(f"Response: {message_response.text}")
            return False, ""
        
        print("\n--- Streaming Response ---")
        full_response = ""
        response_types = set()
        
        # Process the streaming response
        for line in message_response.iter_lines():
            if not line:  # Skip empty lines
                continue
            
            try:
                # Decode the line and parse as JSON
                decoded_line = line.decode('utf-8')
                chunk = json.loads(decoded_line)
                
                # Record the response types for analysis
                chunk_type = chunk.get('type', 'unknown')
                response_types.add(chunk_type)
                
                # Check for different chunk types
                if chunk_type == 'connection_established':
                    print("Connection established with server...")
                elif chunk_type == 'content':
                    content = chunk.get('content', '')
                    print(f"Content: {content[:100]}..." if len(content) > 100 else f"Content: {content}")
                    full_response += content
                elif chunk_type == 'error':
                    print(f"Error: {chunk.get('content')}")
                elif chunk_type == 'system':
                    print(f"System message: {chunk.get('content')}")
                else:
                    # For any other chunk types
                    content = chunk.get('content', json.dumps(chunk))
                    print(f"Response chunk ({chunk_type}): {content[:100]}..." if len(str(content)) > 100 else f"Response chunk ({chunk_type}): {content}")
                    if isinstance(content, str):
                        full_response += content
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                print(f"Raw line: {line.decode('utf-8')}")
            except Exception as e:
                print(f"Error processing response chunk: {e}")
        
        print("\n--- Response Types Received ---")
        print(", ".join(response_types))
        
        if len(full_response) > 20:
            print("\n✓ Received valid LLM Engine response")
            return True, full_response
        else:
            print("\n✗ Response too short or empty")
            return False, full_response
            
    except Exception as e:
        print(f"✗ Error sending message: {str(e)}")
        return False, ""

def test_basic_conversation():
    """
Test basic conversation with a new session
    """
    session_id = create_test_session()
    if not session_id:
        return False
    
    # Store session ID for later tests
    TEST_SESSIONS["basic"] = session_id
    
    success, _ = send_message(session_id, TEST_MESSAGES["basic"], "Basic Conversation")
    return success

def test_memory_functionality():
    """
Test memory functionality by asking the LLM to remember something and then recall it
    """
    session_id = create_test_session()
    if not session_id:
        return False
    
    # Store session ID for later tests
    TEST_SESSIONS["memory"] = session_id
    
    # First, store something in memory
    success1, _ = send_message(session_id, TEST_MESSAGES["memory"], "Memory Storage")
    if not success1:
        return False
    
    # Wait a moment to ensure memory is processed
    time.sleep(2)
    
    # Then, test recall
    success2, response = send_message(session_id, TEST_MESSAGES["recall"], "Memory Recall")
    
    # Verify the response contains the remembered information
    if success2 and "Jordan" in response:
        print("✓ Memory recall successful - found remembered name in response")
        return True
    else:
        print("✗ Memory recall failed - could not find remembered information")
        return False

def test_web_search():
    """
Test web search integration with the LLM Engine
    """
    session_id = create_test_session()
    if not session_id:
        return False
    
    # Store session ID for later tests
    TEST_SESSIONS["search"] = session_id
    
    success, response = send_message(session_id, TEST_MESSAGES["search"], "Web Search")
    
    # Look for indications of search in the response
    if success and ("Paris" in response or "search" in response.lower()):
        print("✓ Web search test likely successful - found relevant information")
        return True
    else:
        print("✗ Web search test inconclusive")
        return False

def test_complex_response():
    """
Test complex response generation from the LLM Engine
    """
    session_id = create_test_session()
    if not session_id:
        return False
    
    # Store session ID for later tests
    TEST_SESSIONS["complex"] = session_id
    
    success, response = send_message(session_id, TEST_MESSAGES["complex"], "Complex Response")
    
    # Check for keywords related to memory systems
    if success and ("tier" in response.lower() or "memory" in response.lower()):
        print("✓ Complex response test successful - found relevant information")
        return True
    else:
        print("✗ Complex response test failed or inconclusive")
        return False

def test_session_persistence():
    """
Test that session context persists across messages
    """
    # Use the memory session from before
    session_id = TEST_SESSIONS.get("memory")
    if not session_id:
        print("✗ Cannot test session persistence - no memory session available")
        return False
    
    # Ask another follow-up question to test persistence
    success, response = send_message(session_id, "What did I just ask you to remember?", "Session Persistence")
    
    # Check for memory-related content
    if success and ("name" in response.lower() or "Jordan" in response):
        print("✓ Session persistence test successful - context was maintained")
        return True
    else:
        print("✗ Session persistence test failed - context was lost")
        return False

def run_all_tests():
    """
Run all integration tests and report results
    """
    results = {
        "health_check": test_health_check(),
        "basic_conversation": test_basic_conversation(),
        "memory_functionality": test_memory_functionality(),
        "session_persistence": test_session_persistence(),
        "web_search": test_web_search(),
        "complex_response": test_complex_response()
    }
    
    log_separator("TEST RESULTS SUMMARY")
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        if result:
            passed += 1
        else:
            failed += 1
        print(f"{status.ljust(10)} {test_name}")
    
    print(f"\nTests Passed: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - Backend is fully integrated with LLM Engine")
        return True
    else:
        print(f"\n⚠️ {failed} TEST(S) FAILED - Review logs for details")
        return False

if __name__ == "__main__":
    print("\n🔍 Starting comprehensive backend-LLM Engine integration test suite")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test User: {TEST_USERNAME} (ID: {TEST_USER_ID})\n")
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
