# Simple test for tiered memory components in Docker environment

import unittest
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class MockRequestParser:
    def __init__(self):
        self.tier_requests = []
        self.episodic_requests = []
    
    def process_response(self, response_text, session_id):
        # Mock processing
        result = {
            "need_regeneration": False,
            "clean_response": response_text
        }
        
        # Check for tier requests
        if "[REQUEST_TIER:" in response_text:
            result["need_regeneration"] = True
            # Simple mock extraction
            import re
            tier_match = re.search(r"\[REQUEST_TIER:(\d+):([\w-]+)\]", response_text)
            if tier_match:
                self.tier_requests.append({
                    "tier": int(tier_match.group(1)),
                    "message_id": tier_match.group(2)
                })
            result["clean_response"] = re.sub(r"\[REQUEST_TIER:\d+:[\w-]+\]", "", response_text)
        
        # Check for episodic requests
        if "[SEARCH_EPISODIC:" in response_text:
            result["need_regeneration"] = True
            import re
            episodic_match = re.search(r"\[SEARCH_EPISODIC:\s*(.+?)\s*\]", response_text)
            if episodic_match:
                result["episodic_query"] = episodic_match.group(1)
                self.episodic_requests.append(result["episodic_query"])
            result["clean_response"] = re.sub(r"\[SEARCH_EPISODIC:\s*(.+?)\s*\]", "", response_text)
            
        return result

class TestTieredMemory(unittest.TestCase):
    def setUp(self):
        self.tier_manager = MockTierManager()
        self.request_parser = MockRequestParser()
        
    def test_tier_generation(self):
        """Test tier generation logic"""
        # Test with user message
        user_message = "I want to learn about quantum computing"
        tiers = self.tier_manager.generate_tiers(user_message, "user")
        
        # Verify tier structure
        self.assertIn("tier1_content", tiers)
        self.assertIn("tier2_content", tiers)
        self.assertLess(len(tiers["tier1_content"]), len(user_message))
        
        # Test with assistant message
        assistant_message = "Quantum computing uses qubits that can exist in multiple states simultaneously."
        tiers = self.tier_manager.generate_tiers(assistant_message, "assistant")
        
        # Verify tiers
        self.assertIn("tier1_content", tiers)
        self.assertIn("tier2_content", tiers)
        self.assertLess(len(tiers["tier1_content"]), len(assistant_message))
    
    def test_tier_request_processing(self):
        """Test processing tier upgrade requests"""
        # Create a test response with a tier request
        message_id = "msg123"
        response = f"I need more context. [REQUEST_TIER:3:{message_id}] Let me look at your question again."
        
        # Process the response
        result = self.request_parser.process_response(response, "session123")
        
        # Verify the result
        self.assertTrue(result["need_regeneration"])
        self.assertNotIn("[REQUEST_TIER:", result["clean_response"])
        self.assertEqual(len(self.request_parser.tier_requests), 1)
        self.assertEqual(self.request_parser.tier_requests[0]["tier"], 3)
        self.assertEqual(self.request_parser.tier_requests[0]["message_id"], message_id)
    
    def test_episodic_request_processing(self):
        """Test processing episodic memory requests"""
        # Create a test response with an episodic request
        response = "I need to check our earlier conversations. [SEARCH_EPISODIC: neural networks]"
        
        # Process the response
        result = self.request_parser.process_response(response, "session123")
        
        # Verify the result
        self.assertTrue(result["need_regeneration"])
        self.assertIn("episodic_query", result)
        self.assertEqual(result["episodic_query"], "neural networks")
        self.assertNotIn("[SEARCH_EPISODIC:", result["clean_response"])

if __name__ == "__main__":
    unittest.main()
