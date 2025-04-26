# Test tiered memory system through API endpoints

import unittest
import logging
import requests
import json
import time
import uuid
import re
import random
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = "http://rai-backend:5001"  # Docker service name
USER_ID = "test_user"
AUTH_HEADERS = {"Authorization": "Bearer test_token"}

# Test data: facts to insert and quiz
TEST_FACTS = [
    ("favorite color", "cerulean blue"),
    ("birthday", "March 15"),
    ("pet", "a golden retriever named Max"),
    ("hobby", "collecting vintage postcards"),
    ("hometown", "Springfield, Illinois"),
    ("favorite food", "spicy Thai curry"),
    ("first job", "lifeguard at the community pool"),
    ("dream vacation", "touring the ancient temples of Japan"),
    ("best friend", "Jamie, who they've known since kindergarten"),
    ("lucky number", "seventeen"),
    ("college major", "Environmental Science"),
    ("favorite book", "The Name of the Wind"),
    ("favorite movie", "The Shawshank Redemption"),
    ("career goal", "to start a sustainable technology company"),
    ("biggest fear", "public speaking"),
    ("favorite season", "autumn when the leaves change"),
    ("allergies", "peanuts and bee stings"),
    ("hidden talent", "can solve a Rubik's cube in under 2 minutes"),
    ("role model", "their grandfather who was an inventor"),
    ("favorite musician", "Beethoven, especially his piano sonatas"),
]

class TieredMemoryAPITest(unittest.TestCase):
    def setUp(self):
        # Create a new chat session for testing
        self.session_id = self._create_chat_session()
        logger.info(f"Created test session with ID: {self.session_id}")
        
        # Storage for facts and quiz results
        self.introduced_facts = []
        self.quiz_results = []
    
    def _create_chat_session(self):
        """Create a new chat session for testing purposes"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/chat-sessions", 
                headers=AUTH_HEADERS,
                json={"userId": USER_ID, "title": f"Memory Test {datetime.now()}"},
                timeout=10
            )
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                return data.get("sessionId")
            else:
                logger.error(f"Failed to create chat session. Status: {response.status_code}")
                # Use a UUID as fallback
                return str(uuid.uuid4())
                
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            return str(uuid.uuid4())
    
    def _send_chat_message(self, message):
        """Send a message to the chat API and return the response"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/chat",
                headers=AUTH_HEADERS,
                json={
                    "sessionId": self.session_id,
                    "userId": USER_ID,
                    "message": message
                },
                timeout=20
            )
            
            if response.status_code != 200:
                logger.error(f"Chat API error: {response.status_code} - {response.text}")
                return "Error: Could not get response from API"
                
            # Parse the response - it's streaming, so we need to get the final chunk
            data = response.json()
            chunks = data.get('chunks', [])
            
            # Extract the actual content from the last chunk with type 'content'
            content_chunks = [chunk for chunk in chunks if chunk.get('type') == 'content']
            if content_chunks:
                return content_chunks[-1].get('content', '')
            
            return "No valid response received"
            
        except Exception as e:
            logger.error(f"Exception in chat API call: {e}")
            return f"Error: {str(e)}"
    
    def _get_conversation_history(self):
        """Retrieve the conversation history for the current session"""
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/chat-history/{self.session_id}",
                headers=AUTH_HEADERS,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"History API error: {response.status_code} - {response.text}")
                return []
                
            data = response.json()
            return data.get('messages', [])
            
        except Exception as e:
            logger.error(f"Exception in history API call: {e}")
            return []
    
    def _extract_facts_from_response(self, response):
        """Look for facts in the response"""
        facts = []
        fact_pattern = r"fact about (.+?): (.+?)$"
        matches = re.findall(fact_pattern, response, re.MULTILINE | re.IGNORECASE)
        
        for key, value in matches:
            facts.append((key.strip(), value.strip()))
        
        return facts

    def test_50_turn_memory_coherence(self):
        """Test the tiered memory system with a 50-turn conversation"""
        # Phase 1: Introduce 50 facts through conversation
        logger.info("=== PHASE 1: Introducing Facts ===")
        
        for turn in range(50):
            # Select a fact (cycling through our test facts)
            fact_key, fact_value = TEST_FACTS[turn % len(TEST_FACTS)]
            
            # Craft a message introducing the fact
            message = f"Turn {turn+1}: I want to tell you a fact about my {fact_key}. My {fact_key} is {fact_value}. Please remember this specific fact."
            logger.info(f"Sending turn {turn+1} with fact: {fact_key} = {fact_value}")
            
            # Send the message
            response = self._send_chat_message(message)
            logger.info(f"Response received: {response[:100]}...")
            
            # Store the introduced fact
            self.introduced_facts.append((fact_key, fact_value))
            
            # Sleep briefly to not overload the API
            time.sleep(1)
        
        logger.info(f"Completed {len(self.introduced_facts)} conversation turns")
        
        # Phase 2: Quiz the system on the facts it should remember
        logger.info("\n=== PHASE 2: Memory Quizzing ===")
        correct_answers = 0
        total_questions = 0
        
        # Create quiz questions for facts we introduced
        for fact_key, fact_value in self.introduced_facts:
            # Only quiz each unique fact once to avoid duplicate questions
            if fact_key not in [q[0] for q in self.quiz_results]:
                # Vary the phrasing to test robustness
                question_formats = [
                    f"What is my {fact_key}?",
                    f"Can you tell me what my {fact_key} is?",
                    f"I previously mentioned my {fact_key}, what was it?"
                ]
                question = random.choice(question_formats)
                logger.info(f"Quizzing on: {question}")
                
                # Send the quiz question
                response = self._send_chat_message(question)
                logger.info(f"Quiz answer: {response[:100]}...")
                
                # Evaluate if the answer contains the correct fact
                is_correct = fact_value.lower() in response.lower()
                total_questions += 1
                
                if is_correct:
                    correct_answers += 1
                    logger.info(f"✓ CORRECT answer for {fact_key}")
                else:
                    logger.info(f"✗ INCORRECT answer for {fact_key}. Expected: {fact_value}")
                
                # Store the results
                self.quiz_results.append((fact_key, fact_value, response, is_correct))
                
                # Sleep briefly between questions
                time.sleep(1)
        
        # Calculate and log the accuracy
        if total_questions > 0:
            accuracy = (correct_answers / total_questions) * 100
            logger.info(f"\n=== QUIZ RESULTS ===")
            logger.info(f"Overall accuracy: {accuracy:.2f}% ({correct_answers}/{total_questions})")
            
            # Detailed breakdown of incorrect answers
            if correct_answers < total_questions:
                logger.info("\nIncorrect answers:")
                for fact_key, fact_value, response, correct in self.quiz_results:
                    if not correct:
                        logger.info(f"Q: What is my {fact_key}?")
                        logger.info(f"   Expected: {fact_value}")
                        logger.info(f"   Got: {response[:100]}...")
            
            # Final assertion - expect at least 50% accuracy
            self.assertGreaterEqual(accuracy, 50.0, f"Memory recall accuracy was only {accuracy:.2f}%")
        else:
            logger.warning("No quiz questions were asked!")

if __name__ == "__main__":
    unittest.main()
