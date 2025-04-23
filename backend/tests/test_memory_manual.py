#!/usr/bin/env python3
# Simple in-place test for contextual memory system

import os
import sys
import json
import logging
from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))) 

# Import the modules we need to test
try:
    from RAI_Chat.backend.services.memory.episodic import EpisodicMemoryManager
    from RAI_Chat.backend.services.memory.contextual import ContextualMemoryManager
    logger.info("Successfully imported memory modules")
except Exception as e:
    logger.error(f"Failed to import memory modules: {e}")
    sys.exit(1)

class TestContextualMemory(unittest.TestCase):
    
    def setUp(self):
        """Set up the test environment"""
        # Mock the LLM API
        self.mock_llm_api = MagicMock()
        self.mock_llm_api.chat_completion.return_value = {"content": "[]"}
        
        # Patch get_llm_api to return our mock
        patcher = patch('RAI_Chat.backend.services.memory.contextual.get_llm_api', 
                         return_value=self.mock_llm_api)
        patcher.start()
        self.addCleanup(patcher.stop)
        
        # Create a mock DB session
        self.mock_db = MagicMock()
        self.mock_user = MagicMock()
        self.mock_user.user_id = 999
        self.mock_user.remembered_facts = []
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Create the episodic memory manager
        self.episodic = EpisodicMemoryManager(user_id=999)
        
        # Create the contextual memory manager
        self.memory = ContextualMemoryManager(user_id=999, episodic_memory_manager=self.episodic)
        
        logger.info("Test setup complete")
    
    def test_session_context_management(self):
        """Test creating and loading session contexts"""
        logger.info("Testing session context management...")
        
        # Create a unique session ID for testing
        session_id = f"test-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Load the session (creates a new one)
        self.memory.load_session_context(session_id)
        
        # Verify session was created correctly
        self.assertEqual(self.memory.active_session_id, session_id)
        self.assertIn('messages', self.memory.active_session_context)
        
        logger.info("Session context management test passed")
    
    def test_three_tier_message_processing(self):
        """Test processing a message with the three-tier structure"""
        logger.info("Testing three-tier message processing...")
        
        # Create a session
        session_id = f"test-session-3tier-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.memory.load_session_context(session_id)
        
        # Create a mock LLM response with three tiers
        response_data = {
            "content": "Main response content",
            "llm_response": {
                "response_tiers": {
                    "tier1": "T1: Brief summary of quantum computing",
                    "tier2": "T2: Extended summary covering quantum computing principles and AI applications",
                    "tier3": "T3: Detailed explanation of quantum computing, qubits, and how they relate to artificial intelligence."
                }
            }
        }
        
        # Process the message
        result = self.memory.process_assistant_message(response_data, "Tell me about quantum computing and AI")
        
        # Verify message was processed correctly
        self.assertTrue(result)
        
        # Verify three-tier structure was stored correctly
        messages = self.memory.active_session_context.get('messages', [])
        self.assertEqual(len(messages), 1)
        
        # Verify tier2 was stored as the context summary
        context_summary = self.memory.active_session_context.get('current_context_summary', '')
        self.assertEqual(context_summary, "T2: Extended summary covering quantum computing principles and AI applications")
        
        logger.info("Three-tier message processing test passed")
    
    def test_memory_pruning(self):
        """Test pruning and archiving when token limit is exceeded"""
        logger.info("Testing memory pruning...")
        
        # Set up episodic mock
        self.episodic.archive_and_summarize_chunk = MagicMock(return_value=True)
        
        # Create a session
        session_id = f"test-session-pruning-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.memory.load_session_context(session_id)
        
        # Override token estimation to force pruning
        original_estimate = self.memory._estimate_turn_tokens
        self.memory._estimate_turn_tokens = lambda turn: 20000  # Force high token count
        
        try:
            # Add messages that will exceed the token limit
            for i in range(2):  # Add 2 messages to exceed 30K token limit
                response_data = {
                    "content": f"Response {i}",
                    "llm_response": {
                        "response_tiers": {
                            "tier1": f"T1: Summary {i}",
                            "tier2": f"T2: Extended summary {i}",
                            "tier3": f"T3: Full content {i}"
                        }
                    }
                }
                
                # Process the message
                self.memory.process_assistant_message(response_data, f"User message {i}")
            
            # Verify archiving was called
            self.episodic.archive_and_summarize_chunk.assert_called_once()
            
            # Verify oldest message was pruned
            self.assertEqual(len(self.memory.active_session_context['messages']), 1)
            self.assertEqual(self.memory.active_session_context['messages'][0]['user_input'], "User message 1")
            
            logger.info("Memory pruning test passed")
            
        finally:
            # Restore original token estimation
            self.memory._estimate_turn_tokens = original_estimate
    
    def test_context_persistence(self):
        """Test saving and loading session context"""
        logger.info("Testing context persistence...")
        
        # Create a session
        session_id = f"test-session-persist-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.memory.load_session_context(session_id)
        
        # Add a test message
        response_data = {
            "content": "Test response",
            "llm_response": {
                "response_tiers": {
                    "tier1": "T1: Test summary",
                    "tier2": "T2: Test extended summary",
                    "tier3": "T3: Test full content"
                }
            }
        }
        
        # Process the message
        self.memory.process_assistant_message(response_data, "Test user input")
        
        # Save the context
        save_result = self.memory.save_session_context()
        self.assertTrue(save_result)
        
        # Clear memory and reload
        self.memory.active_session_id = None
        self.memory.active_session_context = {"messages": []}
        
        # Reload the session
        load_result = self.memory.load_session_context(session_id)
        self.assertTrue(load_result)
        
        # Verify content was preserved
        messages = self.memory.active_session_context.get('messages', [])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['user_input'], "Test user input")
        
        logger.info("Context persistence test passed")

if __name__ == "__main__":
    # Run the tests
    unittest.main()
