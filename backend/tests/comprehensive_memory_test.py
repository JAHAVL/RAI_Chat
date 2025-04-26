#!/usr/bin/env python
"""
Comprehensive memory recall test for the RAI Chat system.
This test simulates the complete memory retrieval cycle, including:
1. Introducing facts in a conversation
2. Tracking message IDs for each fact
3. Testing recall with tier upgrade handling
4. Measuring recall accuracy
"""

import sys
import os
import json
import requests
import uuid
import time
import logging
import re
import random
from typing import Dict, List, Any, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Configuration
API_URL = "http://localhost:6102/api/chat"
HEADERS = {
    "Content-Type": "application/json",
}

class MemoryTester:
    """Tests the RAI Chat memory system by simulating a real conversation."""
    
    def __init__(self):
        """Initialize the tester with a new session."""
        self.session_id = str(uuid.uuid4())
        logger.info(f"Created new session: {self.session_id}")
        
        # Track facts and their message IDs
        self.facts = {}  # fact_key -> {value, message_id, tier}
        self.message_ids = []  # All message IDs in order
        self.message_contents = {}  # message_id -> content
        
        # Define facts to introduce
        self.fact_list = [
            ("favorite color", "cerulean blue"),
            ("birthday", "March 15"),
            ("pet", "a golden retriever named Max"),
            ("hobby", "collecting vintage postcards"),
            ("hometown", "Springfield, Illinois"),
            ("dream job", "wildlife photographer in national parks"),
            ("favorite book", "The Count of Monte Cristo"),
            ("favorite movie", "The Shawshank Redemption"),
            ("favorite food", "spicy Thai curry"),
            ("college major", "environmental science")
        ]
    
    def parse_response(self, response_text: str) -> Dict:
        """Parse the streaming response and extract the JSON content."""
        response_lines = response_text.strip().split('\n')
        
        # Process response lines in reverse order to get the latest JSON
        for line in reversed(response_lines):
            try:
                if '{"type": "content"' in line:
                    # It's a content message
                    json_data = json.loads(line)
                    if "content" in json_data:
                        content_text = json_data["content"]
                        # If content is JSON string, parse it
                        if content_text.startswith('```json') and content_text.endswith('```'):
                            json_str = content_text.replace('```json', '').replace('```', '').strip()
                            return {"content": json.loads(json_str)}
                        return {"content": content_text}
                elif line.startswith('{') and '"content":' in line:
                    # Try direct JSON parsing
                    return json.loads(line)
            except json.JSONDecodeError:
                continue
        
        # If we couldn't parse JSON, return the last line as raw content
        if response_lines:
            return {"content": response_lines[-1]}
        return {"content": ""}
    
    def extract_message_id(self, response_data: Dict) -> Optional[str]:
        """Extract message ID from response data."""
        if "content" in response_data and isinstance(response_data["content"], dict):
            # Get the message ID from the JSON response
            content = response_data["content"]
            if "llm_response" in content:
                # It might be in a format like {"llm_response": {"message_id": "..."}}
                return content.get("llm_response", {}).get("message_id", None)
        
        # Default: generate a random ID if we can't extract one
        return f"msg_{uuid.uuid4().hex[:8]}"
    
    def send_message(self, message: str) -> Tuple[Dict, str]:
        """Send a message and return response data and message ID."""
        payload = {
            "message": message,
            "session_id": self.session_id
        }
        
        try:
            response = requests.post(API_URL, json=payload, headers=HEADERS)
            if response.status_code != 200:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {"content": ""}, ""
            
            response_data = self.parse_response(response.text)
            message_id = self.extract_message_id(response_data)
            
            return response_data, message_id
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"content": ""}, ""
    
    def extract_tier_requests(self, content: str) -> List[Tuple[str, str]]:
        """Extract tier requests from content."""
        if not content:
            return []
        
        # Pattern to match [REQUEST_TIER:level:message_id]
        pattern = r"\[REQUEST_TIER:(\d+):([^\]]+)\]"
        return re.findall(pattern, content)
    
    def extract_episodic_requests(self, content: str) -> List[str]:
        """Extract episodic search requests from content."""
        if not content:
            return []
        
        # Pattern to match [SEARCH_EPISODIC:query]
        pattern = r"\[SEARCH_EPISODIC:([^\]]+)\]"
        return [match.strip() for match in re.findall(pattern, content)]
    
    def simulate_tier_request(self, tier_level: str, message_id: str) -> str:
        """
        Simulate fulfilling a tier request by retrieving the content
        and returning as if we upgraded the tier.
        """
        if message_id in self.message_contents:
            content = self.message_contents[message_id]
            return f"TIER UPGRADE RESULT: Message content at tier {tier_level}: {content}"
        return f"TIER UPGRADE RESULT: Message ID {message_id} not found."
    
    def simulate_episodic_search(self, query: str) -> str:
        """
        Simulate episodic memory search by looking for the query in our facts.
        """
        results = []
        query = query.lower()
        
        for key, data in self.facts.items():
            if query in key.lower() or query in data["value"].lower():
                results.append(f"{key}: {data['value']}")
        
        if results:
            return f"EPISODIC SEARCH RESULTS for '{query}': {'; '.join(results)}"
        else:
            return f"EPISODIC SEARCH RESULTS for '{query}': No matching results found."
    
    def process_requests(self, content: str) -> str:
        """Process tier and episodic requests in a response."""
        # Extract requests
        tier_requests = self.extract_tier_requests(content)
        episodic_requests = self.extract_episodic_requests(content)
        
        processed_response = content
        
        # Process tier requests
        for tier_level, message_id in tier_requests:
            tier_result = self.simulate_tier_request(tier_level, message_id)
            processed_response += f"\n{tier_result}"
        
        # Process episodic requests
        for query in episodic_requests:
            search_result = self.simulate_episodic_search(query)
            processed_response += f"\n{search_result}"
        
        return processed_response
    
    def introduce_facts(self):
        """Introduce all facts to the conversation."""
        logger.info("=== Introducing Facts ===")
        
        for i, (fact_key, fact_value) in enumerate(self.fact_list):
            message = f"Let me tell you about my {fact_key}. It's {fact_value}."
            logger.info(f"Sending fact {i+1}/{len(self.fact_list)}: {message}")
            
            response_data, message_id = self.send_message(message)
            
            # Store the fact and its message ID
            self.facts[fact_key] = {
                "value": fact_value,
                "message_id": message_id,
                "tier": 1  # Start at tier 1
            }
            self.message_ids.append(message_id)
            self.message_contents[message_id] = message
            
            content = response_data.get("content", "")
            if isinstance(content, dict):
                content = json.dumps(content)
            logger.info(f"Response received (ID: {message_id}): {content[:100]}...")
            
            # Add a short delay between messages
            time.sleep(1)
    
    def add_filler_conversation(self, num_messages=5):
        """Add filler messages to push facts out of immediate context."""
        logger.info("=== Adding Filler Conversation ===")
        
        filler_topics = [
            "the weather today",
            "interesting space facts",
            "your favorite season",
            "where you would travel if you could go anywhere",
            "advances in renewable energy",
            "the latest technology news",
            "a good book you've read recently",
            "your thoughts on artificial intelligence",
            "a delicious meal you've had lately",
            "fun weekend activities"
        ]
        
        # Shuffle and select filler topics
        random.shuffle(filler_topics)
        selected_topics = filler_topics[:num_messages]
        
        for i, topic in enumerate(selected_topics):
            message = f"Tell me about {topic}."
            logger.info(f"Sending filler {i+1}/{len(selected_topics)}: {message}")
            
            response_data, message_id = self.send_message(message)
            
            # Store the message ID and content
            self.message_ids.append(message_id)
            self.message_contents[message_id] = message
            
            # Add a short delay between messages
            time.sleep(1)
    
    def test_memory_recall(self):
        """Test memory recall by asking about previously introduced facts."""
        logger.info("=== Testing Memory Recall with Request Processing ===")
        successful_recalls = 0
        
        # Randomize the order of facts for testing
        fact_keys = list(self.facts.keys())
        random.shuffle(fact_keys)
        
        for fact_key in fact_keys:
            fact_value = self.facts[fact_key]["value"]
            
            # Ask about the fact
            quiz_message = f"What is my {fact_key}?"
            logger.info(f"Asking about {fact_key}: {quiz_message}")
            
            # Send the question
            response_data, message_id = self.send_message(quiz_message)
            content = response_data.get("content", "")
            if isinstance(content, dict):
                content = json.dumps(content)
            
            logger.info(f"Initial response: {content[:200]}...")
            
            # Process any tier or episodic requests
            processed_response = self.process_requests(content)
            
            # If we processed requests, send a follow-up to deliver the results
            if processed_response != content:
                logger.info("Found and processed memory retrieval requests")
                logger.info(f"Processed response: {processed_response[:200]}...")
                
                # Send the processed response back as a follow-up message
                follow_up = "Here's the information you requested:"
                logger.info(f"Sending follow-up with retrieved memory: {follow_up}")
                
                follow_up_data, follow_up_id = self.send_message(processed_response)
                follow_up_content = follow_up_data.get("content", "")
                if isinstance(follow_up_content, dict):
                    follow_up_content = json.dumps(follow_up_content)
                
                logger.info(f"Follow-up response: {follow_up_content[:200]}...")
                
                # Check if the fact is in either response
                combined_response = content + " " + follow_up_content
            else:
                combined_response = content
            
            # Check if the response contains the fact value
            if fact_value.lower() in combined_response.lower():
                logger.info(f"✅ SUCCESS: Correctly recalled {fact_key}")
                successful_recalls += 1
            else:
                logger.error(f"❌ FAILURE: Failed to recall {fact_key}")
                
                # Check if requests were made but fact still not found
                tier_requests = self.extract_tier_requests(content)
                episodic_requests = self.extract_episodic_requests(content)
                
                if tier_requests or episodic_requests:
                    logger.info(f"Memory requests were made but fact not recalled:")
                    if tier_requests:
                        logger.info(f"  - Tier requests: {tier_requests}")
                    if episodic_requests:
                        logger.info(f"  - Episodic requests: {episodic_requests}")
            
            # Add a short delay between quiz questions
            time.sleep(1)
        
        # Calculate and report accuracy
        accuracy = (successful_recalls / len(self.facts)) * 100
        logger.info(f"Memory recall accuracy: {accuracy:.2f}% ({successful_recalls}/{len(self.facts)})")
        
        return accuracy

def run_comprehensive_test():
    """Run a comprehensive memory test."""
    logger.info("Starting comprehensive memory test...")
    
    # Create the tester
    tester = MemoryTester()
    
    # Introduce facts
    tester.introduce_facts()
    
    # Add filler conversation to push facts out of immediate context
    tester.add_filler_conversation(num_messages=7)
    
    # Test memory recall
    accuracy = tester.test_memory_recall()
    
    # Return success if accuracy is at least 70%
    return accuracy >= 70

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
