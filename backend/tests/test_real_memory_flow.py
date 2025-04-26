#!/usr/bin/env python
"""
Real-world test of tier requests and episodic memory functionality.
This test simulates actual frontend usage and allows proper time for LLM responses.
"""

import sys
import os
import json
import requests
import uuid
import time
import logging
import re
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration
API_URL = "http://localhost:6102/api/chat"
HEADERS = {
    "Content-Type": "application/json",
}

class RealMemoryFlowTest:
    """Tests memory functionality with proper waiting periods."""
    
    def __init__(self):
        """Initialize the test with a new session."""
        self.session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {self.session_id}")
        
        # Track facts and their message IDs
        self.facts = {}
        self.message_ids = {}
    
    def send_message(self, message: str) -> Dict:
        """
        Send a message to the API and return the response with proper waiting period.
        Simulates a real user interaction with waiting.
        """
        payload = {
            "message": message,
            "session_id": self.session_id
        }
        
        try:
            logger.info(f"Sending message: {message}")
            
            # Make the request
            response = requests.post(API_URL, json=payload, headers=HEADERS)
            
            if response.status_code != 200:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {"error": f"API request failed with status {response.status_code}"}
            
            # Get the response text
            response_text = response.text
            logger.info(f"Raw API response: {response_text[:200]}...")
            
            # Parse the streaming format manually
            lines = response_text.split('\n')
            content_parts = []
            all_data = []
            
            for line in lines:
                if not line.strip():
                    continue
                
                try:
                    # Parse each line as JSON
                    data = json.loads(line)
                    all_data.append(data)
                    
                    # Extract content if available
                    if data.get("type") == "content" and "content" in data:
                        content = data["content"]
                        content_parts.append(content)
                except json.JSONDecodeError:
                    # Skip lines that aren't JSON
                    continue
            
            # Combine all content parts
            combined_content = "".join(content_parts)
            logger.info(f"Full response content: {combined_content[:200]}...")
            
            # Wait 3 seconds to simulate real user reading and thinking before next message
            # This gives the backend time to process any tier requests or episodic searches
            logger.info("Waiting 3 seconds to simulate real user interaction...")
            time.sleep(3)
            
            return {
                "content": combined_content,
                "raw_data": all_data
            }
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def introduce_facts(self):
        """Introduce a series of facts with proper waiting periods."""
        logger.info("=== Introducing Facts ===")
        
        # List of facts to introduce
        facts = [
            "My favorite color is emerald green.",
            "I was born in Barcelona, Spain.",
            "My first car was a blue Honda Civic.",
            "I'm allergic to shellfish.",
            "I graduated from university in 2019."
        ]
        
        # Send each fact and save the response
        for i, fact in enumerate(facts):
            message = f"I want you to remember that {fact}"
            response = self.send_message(message)
            
            if "error" in response:
                logger.error(f"Error introducing fact {i+1}: {response['error']}")
                continue
                
            # Store the fact for later verification
            key_terms = fact.lower().split()[:3]  # Use first few words as key
            key = " ".join(key_terms)
            self.facts[key] = fact
            
            # Wait between facts to simulate real conversation
            time.sleep(2)
    
    def add_filler_conversation(self, count=5):
        """Add filler conversation to push facts out of immediate context."""
        logger.info("=== Adding Filler Conversation ===")
        
        filler_questions = [
            "What's the weather like today?",
            "Can you explain what machine learning is?",
            "Tell me about the history of the internet.",
            "What makes a good movie?",
            "How do airplanes fly?",
            "Explain the concept of supply and demand.",
            "What are some good exercises for beginners?",
            "Can you recommend some productivity tips?",
            "What's the difference between a virus and bacteria?",
            "How does solar energy work?"
        ]
        
        # Use only the requested number of filler questions
        questions_to_use = filler_questions[:count]
        
        for question in questions_to_use:
            response = self.send_message(question)
            if "error" in response:
                logger.error(f"Error in filler conversation: {response['error']}")
            
            # Wait between questions
            time.sleep(2)
    
    def test_memory_recall(self):
        """Test memory recall by asking about previously mentioned facts."""
        logger.info("=== Testing Memory Recall ===")
        
        # Questions that should trigger memory recall
        recall_questions = [
            "What did I tell you about my favorite color?",
            "Where was I born?",
            "What color was my first car?",
            "Do I have any allergies?",
            "When did I graduate from university?"
        ]
        
        successful_recalls = 0
        total_tests = len(recall_questions)
        
        for question in recall_questions:
            response = self.send_message(question)
            
            if "error" in response:
                logger.error(f"Error in memory recall test: {response['error']}")
                continue
                
            content = response.get("content", "")
            
            # Check if response contains any of the facts
            found_fact = False
            for key, fact in self.facts.items():
                if key in question.lower() and any(term in content.lower() for term in fact.lower().split()):
                    logger.info(f"✅ SUCCESS: Response correctly included fact: {fact}")
                    successful_recalls += 1
                    found_fact = True
                    break
            
            if not found_fact:
                logger.error(f"❌ FAILURE: Response didn't recall the relevant fact")
                logger.info(f"Question: {question}")
                logger.info(f"Response: {content[:300]}...")
            
            # Wait between questions
            time.sleep(3)
        
        # Calculate accuracy
        accuracy = (successful_recalls / total_tests) * 100
        logger.info(f"Memory recall accuracy: {accuracy:.2f}% ({successful_recalls}/{total_tests})")
        
        return accuracy
    
    def run_full_test(self):
        """Run a complete real-world memory test."""
        # Step 1: Introduce facts
        self.introduce_facts()
        
        # Step 2: Add filler conversation to push facts out of immediate context
        self.add_filler_conversation(count=7)
        
        # Step 3: Test memory recall
        accuracy = self.test_memory_recall()
        
        # Step 4: Determine pass/fail
        test_passed = accuracy >= 80.0
        logger.info(f"Test {'PASSED' if test_passed else 'FAILED'}")
        
        return {
            "memory_accuracy": accuracy,
            "test_passed": test_passed
        }


if __name__ == "__main__":
    logger.info("Starting real-world memory flow test...")
    tester = RealMemoryFlowTest()
    results = tester.run_full_test()
    sys.exit(0 if results["test_passed"] else 1)
