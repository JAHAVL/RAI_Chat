#!/usr/bin/env python3
"""
Test script to verify that only tier3 responses are returned to the frontend
while all tiers are preserved in memory.
"""

import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the ConversationManager
from RAI_Chat.conversation_manager import ConversationManager


class TestTier3Response(unittest.TestCase):
    """Test that only tier3 responses are sent to frontend."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the memory manager and other dependencies
        self.memory_manager_mock = MagicMock()
        self.contextual_memory_mock = MagicMock()
        self.episodic_memory_mock = MagicMock()
        self.llm_api_mock = MagicMock()
        
        # Create patches for dependencies
        self.memory_patch = patch('RAI_Chat.conversation_manager.MemoryManager', 
                                  return_value=self.memory_manager_mock)
        self.contextual_memory_patch = patch('RAI_Chat.conversation_manager.ContextualMemoryManager', 
                                            return_value=self.contextual_memory_mock)
        self.episodic_memory_patch = patch('RAI_Chat.conversation_manager.EpisodicMemoryManager', 
                                          return_value=self.episodic_memory_mock)
        self.web_search_patch = patch('RAI_Chat.conversation_manager.WebSearchManager')
        self.calendar_patch = patch('RAI_Chat.conversation_manager.CalendarManager')
        self.video_patch = patch('RAI_Chat.conversation_manager.VideoProcessor')
        self.llm_api_patch = patch('RAI_Chat.conversation_manager.get_llm_api', 
                                  return_value=self.llm_api_mock)
        self.llm_engine_patch = patch('RAI_Chat.conversation_manager.get_llm_engine')
        
        # Start all patches
        self.memory_patch.start()
        self.contextual_memory_patch.start()
        self.episodic_memory_patch.start()
        self.web_search_patch.start()
        self.calendar_patch.start()
        self.video_patch.start()
        self.llm_api_patch.start()
        self.llm_engine_patch.start()
        
        # Initialize the conversation manager
        self.conversation_manager = ConversationManager(self.memory_manager_mock)
        
        # Mock methods that we don't want to actually run
        self.conversation_manager._query_needs_more_context = MagicMock(return_value=False)
        self.conversation_manager._is_video_related_query = MagicMock(return_value=False)
        self.conversation_manager._build_system_prompt = MagicMock(return_value="Test system prompt")
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Stop all patches
        self.memory_patch.stop()
        self.contextual_memory_patch.stop()
        self.episodic_memory_patch.stop()
        self.web_search_patch.stop()
        self.calendar_patch.stop()
        self.video_patch.stop()
        self.llm_api_patch.stop()
        self.llm_engine_patch.stop()
    
    def test_tier3_response_returns_only_tier3(self):
        """Test that only tier3 response is returned to frontend."""
        # Mock the LLM API to return a tiered response
        tiered_response = {
            "tier1": "Short response",
            "tier2": "Medium length response with some details",
            "tier3": "Detailed response with complete information that should be sent to frontend"
        }
        self.llm_api_mock.generate_response = MagicMock(return_value=json.dumps(tiered_response))
        
        # Mock the _generate_llm_response to return our tiered response
        self.conversation_manager._generate_llm_response = MagicMock(return_value=tiered_response)
        
        # Process a test message
        test_message = "Hello, this is a test message"
        response = self.conversation_manager.get_response(test_message)
        
        # Verify that only tier3 is returned
        self.assertEqual(response, "Detailed response with complete information that should be sent to frontend")
        
        # Verify that the memory manager received tier3 to store
        self.memory_manager_mock.add_assistant_message.assert_called_once_with(
            "Detailed response with complete information that should be sent to frontend", 
            self.conversation_manager.current_session
        )
        
        # Verify that contextual memory received the full tiered response for storage
        self.contextual_memory_mock.process_assistant_message.assert_called_once()
        args, kwargs = self.contextual_memory_mock.process_assistant_message.call_args
        self.assertEqual(args[0], tiered_response)  # First arg should be the complete tiered response
    
    def test_non_tiered_response_handling(self):
        """Test handling of non-tiered responses."""
        # Mock a non-tiered response
        plain_response = "This is a plain text response without tiers"
        self.conversation_manager._generate_llm_response = MagicMock(return_value=plain_response)
        
        # Process a test message
        test_message = "Another test message"
        response = self.conversation_manager.get_response(test_message)
        
        # Verify that the response is returned as-is
        self.assertEqual(response, "This is a plain text response without tiers")
        
        # Verify that the memory manager received the response to store
        self.memory_manager_mock.add_assistant_message.assert_called_once_with(
            "This is a plain text response without tiers", 
            self.conversation_manager.current_session
        )
        
        # Verify that contextual memory received the response for storage
        self.contextual_memory_mock.process_assistant_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
