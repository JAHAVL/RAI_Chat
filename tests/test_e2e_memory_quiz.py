#!/usr/bin/env python3
# End-to-End Memory Coherence Test
# This test should be run from the host machine, not inside Docker

import requests
import json
import time
import uuid
import random
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[
                        logging.FileHandler("memory_test_results.log"),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

# Connection settings (localhost when running from the host machine)
API_BASE_URL = "http://localhost:6102"  # Updated to match the actual port
USER_ID = "memory_test_user"
AUTH_HEADERS = {"Authorization": "Bearer test_token"}  # Adjust if needed

# Test data: interesting facts to introduce into the conversation
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

class MemoryCoherenceTest:
    def __init__(self):
        # Generate a random session ID
        self.session_id = str(uuid.uuid4())
        self.introduced_facts = []  # Facts introduced in conversation
        self.quiz_results = []      # Results of memory quizzes
        logger.info(f"Using session ID: {self.session_id}")
    
    def send_message(self, message):
        """Send a message to the chat API and return the response"""
        logger.info(f"Sending: {message[:80]}...")
        try:
            # Prepare the request payload
            payload = {
                "message": message
            }
            
            # Optionally include session ID if we already have one from previous messages
            if self.session_id:
                payload["session_id"] = self.session_id
            
            # Send the message to the chat endpoint
            response = requests.post(
                f"{API_BASE_URL}/api/chat",
                headers=AUTH_HEADERS,
                json=payload,
                timeout=30  # Extended timeout for longer responses
            )
            
            if response.status_code != 200:
                logger.error(f"Chat API error: {response.status_code} - {response.text}")
                return "Error: Could not get response from API"
            
            # Extract session ID from response if we don't have one yet
            try:
                data = response.json()
                if not self.session_id and 'session_id' in data:
                    self.session_id = data['session_id']
                    logger.info(f"Received session ID: {self.session_id}")
            except:
                pass
                
            # Parse the response - it might be streaming or chunked in various formats
            try:
                data = response.json()
                
                # Handle different response formats
                if 'chunks' in data:
                    # Streaming response format
                    chunks = data.get('chunks', [])
                    content_chunks = [chunk for chunk in chunks if chunk.get('type') == 'content']
                    if content_chunks:
                        result = content_chunks[-1].get('content', '')
                    else:
                        result = "No content chunks received"
                elif 'response' in data:
                    # Direct response format
                    result = data.get('response', '')
                else:
                    # Try to extract any text content
                    result = str(data)
                    
                logger.info(f"Received: {result[:80]}...")
                return result
                
            except ValueError:
                # Not JSON, return raw text
                result = response.text
                logger.info(f"Received non-JSON: {result[:80]}...")
                return result
            
        except Exception as e:
            logger.error(f"Exception in chat API call: {e}")
            return f"Error: {str(e)}"
    
    def run_conversation_test(self, num_turns=50):
        """Run a multi-turn conversation test introducing facts"""
        logger.info(f"===== STARTING {num_turns}-TURN CONVERSATION TEST =====")
        
        # Phase 1: Introduce facts in conversation
        logger.info("\n----- PHASE 1: INTRODUCING FACTS -----")
        
        for turn in range(num_turns):
            # Select a fact (cycling through our test facts)
            fact_key, fact_value = TEST_FACTS[turn % len(TEST_FACTS)]
            
            # Craft a message introducing the fact
            message = f"Turn {turn+1}: I want to tell you a fact about my {fact_key}. My {fact_key} is {fact_value}. Please remember this specific fact."
            
            # Send the message
            response = self.send_message(message)
            
            # Check if response contains error
            if response.startswith("Error:"):
                logger.error(f"Error in conversation turn {turn+1}: {response}")
                # Try to continue with next turn
                continue
            
            # Store the introduced fact
            self.introduced_facts.append((fact_key, fact_value))
            
            # Sleep briefly to not overload the API
            time.sleep(1)
        
        logger.info(f"Completed {len(self.introduced_facts)} conversation turns")
        
        # Phase 2: Quiz the system on the facts it should remember
        logger.info("\n----- PHASE 2: MEMORY QUIZZING -----")
        correct_answers = 0
        total_questions = 0
        
        # Create quiz questions for facts we introduced
        unique_facts = {}
        for fact_key, fact_value in self.introduced_facts:
            unique_facts[fact_key] = fact_value
            
        # Quiz on each unique fact
        for fact_key, fact_value in unique_facts.items():
            # Vary the phrasing to test robustness
            question_formats = [
                f"What is my {fact_key}?",
                f"Can you tell me what my {fact_key} is?",
                f"I previously mentioned my {fact_key}, what was it?"
            ]
            question = random.choice(question_formats)
            logger.info(f"Quizzing on: {question}")
            
            # Send the quiz question
            response = self.send_message(question)
            
            # Skip evaluation if there was an error
            if response.startswith("Error:"):
                logger.error(f"Error during quiz: {response}")
                continue
            
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
            logger.info(f"\n===== QUIZ RESULTS =====")
            logger.info(f"Overall accuracy: {accuracy:.2f}% ({correct_answers}/{total_questions})")
            
            # Detailed breakdown of incorrect answers
            if correct_answers < total_questions:
                logger.info("\nIncorrect answers:")
                for fact_key, fact_value, response, correct in self.quiz_results:
                    if not correct:
                        logger.info(f"Q: What is my {fact_key}?")
                        logger.info(f"   Expected: {fact_value}")
                        logger.info(f"   Got: {response[:150]}...")
            
            return accuracy
        else:
            logger.warning("No quiz questions were asked!")
            return 0.0

if __name__ == "__main__":
    # Run the test
    test = MemoryCoherenceTest()
    accuracy = test.run_conversation_test(num_turns=50)
    
    # Report final result
    if accuracy >= 50.0:
        logger.info(f"✓✓✓ TEST PASSED: Memory recall accuracy was {accuracy:.2f}%")
        exit(0)
    else:
        logger.error(f"✗✗✗ TEST FAILED: Memory recall accuracy was only {accuracy:.2f}%")
        exit(1)
