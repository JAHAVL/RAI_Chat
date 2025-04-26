# Simple test for tiered memory components

import sys
import os
import logging
import unittest
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Create a simple mock tier manager for testing
class MockTierManager:
    def generate_tiers(self, content, role):
        # Generate simplified tiers for testing
        words = content.split()
        
        # Tier 1: First few words or key-value
        if len(words) <= 5:
            tier1 = content
        else:
            tier1 = " ".join(words[:5]) + "..."
        
        # Tier 2: Truncated content
        if len(content) <= 20:
            tier2 = content
        else:
            tier2 = content[:20] + "..."
            
        return {
            "tier1_content": tier1,
            "tier2_content": tier2
        }

# Define basic Message class for testing
class Message:
    def __init__(self, message_id, session_id, user_id, content, 
                 tier1_content, tier2_content, required_tier_level, role):
        self.message_id = message_id
        self.session_id = session_id
        self.user_id = user_id
        self.content = content
        self.tier1_content = tier1_content
        self.tier2_content = tier2_content
        self.required_tier_level = required_tier_level
        self.role = role
        self.timestamp = datetime.now()

# Define mock RequestParser for testing
class MockRequestParser:
    def __init__(self):
        self.messages = {}
    
    def add_message(self, message):
        self.messages[message.message_id] = message
    
    def process_response(self, response_text, session_id):
        # Check for tier requests
        result = {
            "need_regeneration": False,
            "clean_response": response_text
        }
        
        # Simple pattern matching for tier requests
        import re
        tier_pattern = r"\[REQUEST_TIER:(\d+):([\w-]+)\]"
        episodic_pattern = r"\[SEARCH_EPISODIC:\s*(.+?)\s*\]"
        
        # Process tier requests
        for match in re.finditer(tier_pattern, response_text):
            tier = int(match.group(1))
            msg_id = match.group(2)
            
            if msg_id in self.messages:
                if tier > self.messages[msg_id].required_tier_level:
                    self.messages[msg_id].required_tier_level = tier
                    result["need_regeneration"] = True
        
        # Clean response
        clean_response = re.sub(tier_pattern, "", response_text)
        result["clean_response"] = clean_response
        
        # Process episodic requests
        episodic_match = re.search(episodic_pattern, clean_response)
        if episodic_match:
            result["need_regeneration"] = True
            result["episodic_query"] = episodic_match.group(1)
            result["clean_response"] = re.sub(episodic_pattern, "", clean_response)
        
        return result

# Define mock ContextBuilder for testing
class MockContextBuilder:
    def __init__(self):
        self.messages = {}
    
    def add_message(self, message):
        self.messages[message.message_id] = message
    
    def build_tiered_context(self, current_message, session_id, user_id, 
                            include_episodic=False, episodic_context=None):
        # Build context with appropriate tier levels
        context_msgs = []
        
        for msg_id, msg in self.messages.items():
            content = None
            
            # Select content based on required tier level
            if msg.required_tier_level == 1 and msg.tier1_content:
                content = msg.tier1_content
            elif msg.required_tier_level == 2 and msg.tier2_content:
                content = msg.tier2_content
            else:
                content = msg.content
            
            context_msgs.append({
                "role": msg.role,
                "content": content,
                "message_id": msg.message_id
            })
        
        # Sort by timestamp (assuming they have timestamps)
        context_msgs.sort(key=lambda x: self.messages[x["message_id"]].timestamp)
        
        # Add episodic context if requested
        if include_episodic and episodic_context:
            context_msgs.append({
                "role": "system",
                "content": f"Episodic memory: {episodic_context}"
            })
        
        # Return the context
        return {
            "messages": context_msgs,
            "current_message": current_message
        }

# Test cases
class TestTieredMemory(unittest.TestCase):
    def setUp(self):
        self.tier_manager = MockTierManager()
        self.request_parser = MockRequestParser()
        self.context_builder = MockContextBuilder()
        self.session_id = str(uuid.uuid4())
        self.user_id = "test_user"
    
    def test_tier_generation(self):
        """Test tier generation functionality"""
        # Test with user message
        user_message = "I want to learn about quantum computing and its applications"
        tiers = self.tier_manager.generate_tiers(user_message, "user")
        
        self.assertIn("tier1_content", tiers)
        self.assertIn("tier2_content", tiers)
        self.assertLess(len(tiers["tier1_content"]), len(user_message))
        
        # Test with assistant message
        assistant_message = "Quantum computing uses quantum bits or qubits that can exist in multiple states simultaneously."
        tiers = self.tier_manager.generate_tiers(assistant_message, "assistant")
        
        self.assertIn("tier1_content", tiers)
        self.assertIn("tier2_content", tiers)
        self.assertLess(len(tiers["tier1_content"]), len(assistant_message))
    
    def test_tier_requests(self):
        """Test tier request parsing and processing"""
        # Create some test messages
        msg1_id = "msg1"
        msg1_content = "What is quantum entanglement?"
        msg1_tiers = self.tier_manager.generate_tiers(msg1_content, "user")
        msg1 = Message(
            message_id=msg1_id,
            session_id=self.session_id,
            user_id=self.user_id,
            content=msg1_content,
            tier1_content=msg1_tiers["tier1_content"],
            tier2_content=msg1_tiers["tier2_content"],
            required_tier_level=1,
            role="user"
        )
        
        # Add message to request parser and context builder
        self.request_parser.add_message(msg1)
        self.context_builder.add_message(msg1)
        
        # Test response with tier request
        test_response = f"I need more context. [REQUEST_TIER:3:{msg1_id}] Let me check that question again."
        processed = self.request_parser.process_response(test_response, self.session_id)
        
        # Verify processing results
        self.assertTrue(processed["need_regeneration"])
        self.assertNotIn("[REQUEST_TIER:", processed["clean_response"])
        
        # Verify message tier level was updated
        self.assertEqual(self.request_parser.messages[msg1_id].required_tier_level, 3)
        
        # Verify context builder uses the right tier level
        context = self.context_builder.build_tiered_context(
            current_message="Another question",
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        # Find our message in the context
        for msg in context["messages"]:
            if msg["message_id"] == msg1_id:
                # Should use full content (tier 3)
                self.assertEqual(msg["content"], msg1_content)
    
    def test_episodic_requests(self):
        """Test episodic memory request parsing"""
        # Test response with episodic memory request
        test_response = "I need to check our earlier conversation. [SEARCH_EPISODIC: neural networks]"
        processed = self.request_parser.process_response(test_response, self.session_id)
        
        # Verify processing results
        self.assertTrue(processed["need_regeneration"])
        self.assertIn("episodic_query", processed)
        self.assertEqual(processed["episodic_query"], "neural networks")
        self.assertNotIn("[SEARCH_EPISODIC:", processed["clean_response"])

if __name__ == "__main__":
    unittest.main()
