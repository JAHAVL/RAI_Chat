# RAI_Chat/backend/tests/test_memory_system.py

import os
import sys
import unittest
import json
import logging
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_memory_system')

# Create all necessary mocks before importing any modules
class MockPathModule:
    """Mock for the path utility module"""
    @staticmethod
    def ensure_directory_exists(path):
        os.makedirs(path, exist_ok=True)
        return path
    
    @staticmethod
    def get_user_base_dir(user_id):
        return Path(f"/tmp/test_user_{user_id}")
    
    @staticmethod
    def get_user_session_context_filepath(user_id, session_id):
        return Path(f"/tmp/test_user_{user_id}/{session_id}_context.json")

# Create a mock for llm_Engine
class MockLLMAPI:
    def chat_completion(self, messages, **kwargs):
        # Return a mock extraction result
        return {"content": "[\"User likes Python\", \"User prefers detailed explanations\"]"}

class MockModels:
    """Mock for database models"""
    class User:
        def __init__(self, user_id):
            self.user_id = user_id
            self.remembered_facts = []

# Add mocks to sys.modules
sys.modules['llm_Engine'] = MagicMock()
sys.modules['llm_Engine.llm_api_bridge'] = MagicMock()
sys.modules['llm_Engine.llm_api_bridge'].get_llm_api = MagicMock(return_value=MockLLMAPI())

sys.modules['RAI_Chat.backend.utils.path'] = MockPathModule()
sys.modules['RAI_Chat.backend.utils'] = MagicMock()
sys.modules['RAI_Chat.backend.utils.path'] = MockPathModule()

sys.modules['core.database.models'] = MockModels()

# Patch path utils at the module level
patch('services.memory.contextual.get_user_base_dir', MockPathModule.get_user_base_dir).start()
patch('services.memory.contextual.get_user_session_context_filepath', MockPathModule.get_user_session_context_filepath).start()
patch('services.memory.contextual.ensure_directory_exists', MockPathModule.ensure_directory_exists).start()
patch('services.memory.episodic.ensure_directory_exists', MockPathModule.ensure_directory_exists).start()
patch('services.memory.contextual.LOGS_DIR', Path('/tmp/logs')).start()
patch('services.memory.episodic.LOGS_DIR', Path('/tmp/logs')).start()
patch('services.memory.episodic.DATA_DIR', Path('/tmp/data')).start()

# Define our test class
class TestContextualMemory(unittest.TestCase):
    """Test the three-tier contextual memory system"""
    
    def setUp(self):
        """Set up the test environment"""
        logger.info("Setting up test environment...")
        
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, 'logs'), exist_ok=True)
        
        # Set up path mocks
        patch('services.memory.contextual.get_user_base_dir', 
              lambda uid: Path(os.path.join(self.test_dir, f'user_{uid}'))).start()
        patch('services.memory.contextual.get_user_session_context_filepath', 
              lambda uid, sid: Path(os.path.join(self.test_dir, f'user_{uid}', f'{sid}_context.json'))).start()
        
        # Create the mock database session
        self.mock_db = MagicMock()
        self.mock_user = MockModels.User(999)
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Create our episodic memory manager
        self.episodic = MagicMock()
        self.episodic.archive_and_summarize_chunk.return_value = True
        
        # Import after patching
        from services.memory.contextual import ContextualMemoryManager
        
        # Create our contextual memory manager
        self.memory = ContextualMemoryManager(user_id=999, episodic_memory_manager=self.episodic)
        
        logger.info("Test environment setup complete.")
        
    def tearDown(self):
        """Clean up after the test"""
        # Remove temporary directories
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
        # Stop all patches
        patch.stopall()
        
    def test_session_context_management(self):
        """Test creating, saving, and loading session contexts"""
        logger.info("Testing session context management...")
        
        # 1. Create and save a new session
        session_id = "test-session-1"
        self.memory.load_session_context(session_id)
        
        # Add a message to the session
        self.memory.active_session_context['messages'] = [
            {
                "turn_id": "turn-1",
                "timestamp": datetime.now().isoformat(),
                "user_input": "Hello AI",
                "llm_output": {"content": "Hello human", "llm_response": {"response_tiers": {"tier1": "Greeting", "tier2": "Extended greeting", "tier3": "Hello human"}}}
            }
        ]
        
        # Save the session
        self.memory.save_session_context()
        
        # Reset the memory context
        self.memory.active_session_id = None
        self.memory.active_session_context = {"messages": []}
        
        # 2. Load the existing session again
        self.memory.load_session_context(session_id)
        
        # Check if the message was loaded
        self.assertEqual(len(self.memory.active_session_context['messages']), 1)
        self.assertEqual(self.memory.active_session_context['messages'][0]['user_input'], "Hello AI")
        
        logger.info("Session context management test passed.")
    
    def test_user_remembered_facts(self):
        """Test storing and retrieving user facts"""
        logger.info("Testing user facts management...")
        
        # Set initial facts
        self.mock_user.remembered_facts = ["User likes pizza"]
        
        # Load facts
        self.memory.load_user_remembered_facts(self.mock_db)
        self.assertEqual(self.memory.user_remembered_facts, ["User likes pizza"])
        
        # Add a new fact
        self.memory.user_remembered_facts.append("User is learning Python")
        
        # Save facts
        self.memory.save_user_remembered_facts(self.mock_db)
        
        # Check if the database was updated
        self.assertEqual(self.mock_user.remembered_facts, 
                         ["User likes pizza", "User is learning Python"])
        
        logger.info("User facts management test passed.")
    
    def test_forget_command(self):
        """Test forgetting specific facts"""
        logger.info("Testing forget command...")
        
        # Set initial facts
        self.memory.user_remembered_facts = [
            "User likes pizza", 
            "User dislikes broccoli", 
            "User is learning Python"
        ]
        
        # Test forgetting a fact
        result = self.memory.process_forget_command(self.mock_db, "forget that I dislike broccoli")
        
        # Check the result
        self.assertTrue(result)
        self.assertEqual(len(self.memory.user_remembered_facts), 2)
        self.assertNotIn("User dislikes broccoli", self.memory.user_remembered_facts)
        
        logger.info("Forget command test passed.")
    
    def test_three_tier_processing(self):
        """Test the three-tier memory system"""
        logger.info("Testing three-tier memory system...")
        
        # Set up a test session
        session_id = "test-session-3tier"
        self.memory.load_session_context(session_id)
        
        # Create a mock LLM response with the three-tier structure
        response_data = {
            "content": "This is the main response",
            "llm_response": {
                "response_tiers": {
                    "tier1": "T1: Short summary",
                    "tier2": "T2: Medium summary with more details about the conversation",
                    "tier3": "T3: This is the full detailed response that would be shown to the user"
                }
            }
        }
        
        # Process the message
        result = self.memory.process_assistant_message(response_data, "Test user input")
        
        # Verify tier2 was stored as the current context summary
        self.assertEqual(
            self.memory.active_session_context['current_context_summary'],
            "T2: Medium summary with more details about the conversation"
        )
        
        # Verify the turn was stored with all tiers
        self.assertEqual(len(self.memory.active_session_context['messages']), 1)
        stored_turn = self.memory.active_session_context['messages'][0]
        self.assertEqual(stored_turn['user_input'], "Test user input")
        self.assertEqual(stored_turn['llm_output'], response_data)
        
        logger.info("Three-tier memory system test passed.")
    
    def test_memory_extraction(self):
        """Test memory extraction from conversations"""
        logger.info("Testing memory extraction...")
        
        # Set up mock LLM API to return specific memories
        with patch('llm_Engine.llm_api_bridge.get_llm_api', return_value=MockLLMAPI()):
            # Set up a test session
            session_id = "test-session-extract"
            self.memory.load_session_context(session_id)
            
            # Create a mock response that should trigger memory extraction
            response_data = {
                "content": "I'll remember your preferences",
                "llm_response": {
                    "response_tiers": {
                        "tier1": "T1: Noted preferences",
                        "tier2": "T2: Acknowledged user preferences",
                        "tier3": "T3: I understand that you like Python and prefer detailed explanations. I'll remember that for our future conversations."
                    }
                }
            }
            
            # Before extraction
            self.memory.user_remembered_facts = []
            
            # Process the message
            self.memory.process_assistant_message(response_data, "I like Python and prefer detailed explanations.")
            
            # Verify memories were extracted
            self.assertEqual(len(self.memory.user_remembered_facts), 2)
            self.assertIn("User likes Python", self.memory.user_remembered_facts)
            self.assertIn("User prefers detailed explanations", self.memory.user_remembered_facts)
        
        logger.info("Memory extraction test passed.")
    
    def test_pruning_and_archiving(self):
        """Test pruning and archiving memory when token limit is exceeded"""
        logger.info("Testing pruning and archiving...")
        
        # Set up a test session
        session_id = "test-session-prune"
        self.memory.load_session_context(session_id)
        
        # Set a lower token limit for testing
        with patch.object(self.memory, 'ACTIVE_TOKEN_LIMIT', 1000):
            # Create messages that will exceed the token limit
            # Force _estimate_turn_tokens to return a high value
            with patch.object(self.memory, '_estimate_turn_tokens', return_value=800):
                # Add two messages (each 800 tokens) to exceed the 1000 token limit
                for i in range(2):
                    response_data = {
                        "content": f"Response {i}",
                        "llm_response": {
                            "response_tiers": {
                                "tier1": f"T1: Summary {i}",
                                "tier2": f"T2: Extended summary {i}",
                                "tier3": f"T3: Full response {i}"
                            }
                        }
                    }
                    self.memory.process_assistant_message(response_data, f"Input {i}")
                
                # Verify that archiving was called
                self.episodic.archive_and_summarize_chunk.assert_called_once()
                
                # Verify that older messages were pruned
                self.assertEqual(len(self.memory.active_session_context['messages']), 1)
                # The remaining message should be the latest one
                self.assertEqual(self.memory.active_session_context['messages'][0]['user_input'], "Input 1")
        
        logger.info("Pruning and archiving test passed.")

if __name__ == '__main__':
    unittest.main()
