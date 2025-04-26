#!/usr/bin/env python
"""
Test to evaluate the backend's actual handling of tier requests and episodic searches.
This test works with the real API to confirm if tier requests and episodic searches are 
properly processed by the backend to regenerate responses with the retrieved information.
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

class TierRequestTester:
    """Evaluates the backend's tier request and episodic search handling."""
    
    def __init__(self):
        """Initialize the tester with a new session."""
        self.session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {self.session_id}")
        
        # Track facts and their message IDs
        self.facts = {}
        self.message_history = []
    
    def send_message(self, message: str, save_to_history=True) -> Dict:
        """Send a message to the API and return the response."""
        payload = {
            "message": message,
            "session_id": self.session_id
        }
        
        try:
            logger.info(f"Sending message: {message}")
            
            # Make a normal POST request, without stream=True
            response = requests.post(API_URL, json=payload, headers=HEADERS)
            
            if response.status_code != 200:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {"raw_content": ""}
            
            # Get the response text
            response_text = response.text
            logger.info(f"Raw API response: {response_text[:500]}...")
            
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
            
            # Log all JSON data from the response to check for special commands
            logger.info(f"All response data objects: {json.dumps(all_data, indent=2)[:500]}...")
            
            # Try to extract JSON from the combined content
            result = {"raw_content": combined_content}
            
            logger.info(f"Received response: {combined_content[:200]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return {"raw_content": ""}
    
    def introduce_facts(self):
        """Introduce a series of facts to the conversation."""
        logger.info("=== Introducing Facts ===")
        
        # List of facts to introduce
        fact_pairs = [
            ("favorite animal", "The capybara"),
            ("childhood pet", "A calico cat named Whiskers"),
            ("first job", "A barista at a local coffee shop"),
            ("favorite instrument", "The cello"),
            ("college degree", "A Bachelor's in Marine Biology"),
            ("dream vacation", "A month-long tour of Japan"),
            ("favorite book", "One Hundred Years of Solitude"),
            ("least favorite food", "Brussels sprouts"),
            ("lucky number", "Seventeen"),
            ("favorite season", "Autumn, for the colorful leaves")
        ]
        
        # Send each fact as a separate message
        for key, value in fact_pairs:
            message = f"I want you to remember that my {key} is {value}."
            response = self.send_message(message)
            
            # Store the fact
            self.facts[key] = value
            
            # Add a delay between messages
            time.sleep(1)
    
    def add_filler_conversation(self, count=10):
        """Add filler conversation to push facts out of immediate context."""
        logger.info("=== Adding Filler Conversation ===")
        
        # List of general questions that don't reference facts
        filler_questions = [
            "Tell me about the history of chocolate.",
            "What are some interesting facts about deep sea creatures?",
            "Explain how solar panels work.",
            "What are the benefits of meditation?",
            "Tell me about the Renaissance period in Europe.",
            "How does machine learning work?",
            "What makes a good novel?",
            "Explain the concept of black holes.",
            "What are some sustainable living practices?",
            "How do vaccines work?",
            "Tell me about the cultural significance of tea ceremonies.",
            "What are the major theories about dinosaur extinction?",
            "Explain the basics of quantum computing.",
            "How has cinema evolved over the last century?",
            "What are some ancient wonders of the world?"
        ]
        
        # Ask a subset of the filler questions
        for i in range(min(count, len(filler_questions))):
            response = self.send_message(filler_questions[i])
            
            # Add a delay between messages
            time.sleep(1)
    
    def test_tier_requests(self):
        """Test the backend's handling of tier requests."""
        logger.info("=== Testing Tier Request Handling ===")
        
        # List of test questions that should trigger tier requests
        test_questions = [
            "Can you remind me what my favorite animal was?",
            "Can you remind me what my childhood pet was?",
            "What instrument did I tell you I like the most?",
            "What did I study in college?",
            "What's my lucky number?"
        ]
        
        successful_recalls = 0
        total_tests = len(test_questions)
        
        for question in test_questions:
            # Send the question
            response = self.send_message(question)
            content = response.get("raw_content", "")
            
            # Log the full response to see if it contains special commands
            logger.info(f"FULL RESPONSE for '{question}':\n{content}")
            
            # Check if the response contains tier request markers
            tier_request_pattern = r"\[REQUEST_TIER:(\d+):[^\]]+\]"
            tier_requests = re.findall(tier_request_pattern, content)
            if tier_requests:
                logger.info(f"Found {len(tier_requests)} tier requests: {tier_requests}")
            
            # Check if the response contains the corresponding fact
            found_fact = False
            for key, value in self.facts.items():
                if key in question.lower() and value.lower() in content.lower():
                    logger.info(f"✅ SUCCESS: Response correctly included fact: {key} = {value}")
                    successful_recalls += 1
                    found_fact = True
                    break
            
            if not found_fact:
                logger.error(f"❌ FAILURE: Response did not contain the expected fact")
                logger.info(f"Question: {question}")
                logger.info(f"Response: {content[:200]}...")
            
            # Add a delay between tests
            time.sleep(1)
        
        # Calculate accuracy
        accuracy = (successful_recalls / total_tests) * 100
        logger.info(f"Tier request handling accuracy: {accuracy:.2f}% ({successful_recalls}/{total_tests})")
        
        return accuracy
    
    def test_episodic_search(self):
        """Test the backend's handling of episodic search requests."""
        logger.info("=== Testing Episodic Search Handling ===")
        
        # List of test questions that should trigger episodic search
        test_questions = [
            "What was my least favorite food?",
            "Tell me about my dream vacation.",
            "What did I say about my first job?",
            "Which season do I like the most?",
            "What book did I mention as my favorite?"
        ]
        
        successful_recalls = 0
        total_tests = len(test_questions)
        
        for question in test_questions:
            # Send the question
            response = self.send_message(question)
            content = response.get("raw_content", "")
            
            # Log the full response to see if it contains special commands
            logger.info(f"FULL RESPONSE for '{question}':\n{content}")
            
            # Check if the response contains episodic search markers
            episodic_search_pattern = r"\[SEARCH_EPISODIC:([^\]]+)\]"
            episodic_searches = re.findall(episodic_search_pattern, content)
            if episodic_searches:
                logger.info(f"Found episodic search requests: {episodic_searches}")
            
            # Check if the response contains the corresponding fact
            found_fact = False
            for key, value in self.facts.items():
                if key in question.lower() and value.lower() in content.lower():
                    logger.info(f"✅ SUCCESS: Response correctly included fact through episodic search: {key} = {value}")
                    successful_recalls += 1
                    found_fact = True
                    break
            
            if not found_fact:
                logger.error(f"❌ FAILURE: Response did not contain the expected fact")
                logger.info(f"Question: {question}")
                logger.info(f"Response: {content[:200]}...")
            
            # Add a delay between tests
            time.sleep(1)
        
        # Calculate accuracy
        accuracy = (successful_recalls / total_tests) * 100
        logger.info(f"Episodic search handling accuracy: {accuracy:.2f}% ({successful_recalls}/{total_tests})")
        
        return accuracy
    
    def run_full_test(self):
        """Run a complete test of tier request and episodic search handling."""
        # Step 1: Introduce facts
        self.introduce_facts()
        
        # Step 2: Add filler conversation to push facts out of immediate context
        self.add_filler_conversation(count=10)
        
        # Step 3: Test tier request handling
        tier_accuracy = self.test_tier_requests()
        
        # Step 4: Test episodic search handling
        episodic_accuracy = self.test_episodic_search()
        
        # Step 5: Calculate overall accuracy
        overall_accuracy = (tier_accuracy + episodic_accuracy) / 2
        logger.info(f"Overall accuracy: {overall_accuracy:.2f}%")
        
        # Step 6: Determine pass/fail
        test_passed = overall_accuracy >= 70.0
        logger.info(f"Test {'PASSED' if test_passed else 'FAILED'}")
        
        return {
            "tier_accuracy": tier_accuracy,
            "episodic_accuracy": episodic_accuracy,
            "overall_accuracy": overall_accuracy,
            "test_passed": test_passed
        }

if __name__ == "__main__":
    logger.info("Starting tier request and episodic search handling test...")
    tester = TierRequestTester()
    results = tester.run_full_test()
    sys.exit(0 if results["test_passed"] else 1)
