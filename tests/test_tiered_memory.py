# RAI_Chat/tests/test_tiered_memory.py

import unittest
import sys
import os
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create __init__.py file in mocks directory if it doesn't exist
mocks_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mocks')
os.makedirs(mocks_dir, exist_ok=True)
init_file = os.path.join(mocks_dir, '__init__.py')
if not os.path.exists(init_file):
    with open(init_file, 'w') as f:
        pass  # Create empty __init__.py file

# Import the necessary modules
from tests.mocks.mock_tier_manager import MockTierManager
from backend.managers.memory.context_builder import ContextBuilder
from backend.managers.memory.request_parser import RequestParser
from backend.managers.memory.memory_pruner import MemoryPruner
from backend.core.database.models import Message
from backend.core.database.connection import get_db, engine, Base
from sqlalchemy.orm import sessionmaker

class TestTieredMemory(unittest.TestCase):
    """Test the tiered memory system components."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test environment."""
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Create a session factory
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create components
        cls.tier_manager = MockTierManager()
        
    def setUp(self):
        """Set up a fresh database session for each test."""
        self.db = self.SessionLocal()
        
        # Initialize components that need database access
        self.context_builder = ContextBuilder(self.db)
        self.request_parser = RequestParser(self.db)
        self.memory_pruner = MemoryPruner(self.db, None, token_limit=5000)
        
        # Generate a unique session ID for each test
        self.session_id = str(uuid.uuid4())
        self.user_id = '123'  # Test user ID
        
    def tearDown(self):
        """Clean up after each test."""
        # Delete all test messages
        self.db.query(Message).filter_by(session_id=self.session_id).delete()
        self.db.commit()
        self.db.close()
    
    def test_tier_generation(self):
        """Test generation of tiered representations."""
        # Test user message tier generation
        user_message = "I'm interested in understanding how quantum computers work."
        user_tiers = self.tier_manager.generate_tiers(user_message, "user")
        
        # Verify tier structure
        self.assertIn("tier1_content", user_tiers)
        self.assertIn("tier2_content", user_tiers)
        
        # Ensure tiers are progressively more compact
        self.assertLess(len(user_tiers["tier1_content"]), len(user_tiers["tier2_content"]))
        self.assertLess(len(user_tiers["tier2_content"]), len(user_message))
        
        # Test assistant message tier generation
        assistant_message = "Quantum computers use quantum bits or qubits, which can exist in multiple states simultaneously unlike classical bits. This property, known as superposition, allows quantum computers to perform certain calculations much faster than traditional computers."
        assistant_tiers = self.tier_manager.generate_tiers(assistant_message, "assistant")
        
        # Verify tiers
        self.assertIn("tier1_content", assistant_tiers)
        self.assertIn("tier2_content", assistant_tiers)
        self.assertLess(len(assistant_tiers["tier1_content"]), len(assistant_tiers["tier2_content"]))
        
    def test_message_storage_and_retrieval(self):
        """Test storing and retrieving messages with tiers."""
        # Create a few messages
        messages = [
            {
                "role": "user",
                "content": "Hello! Can you tell me about machine learning?"
            },
            {
                "role": "assistant",
                "content": "Machine learning is a field of artificial intelligence that enables computers to learn from data and improve over time without explicit programming."
            },
            {
                "role": "user",
                "content": "What are some common machine learning algorithms?"
            },
            {
                "role": "assistant",
                "content": "Common machine learning algorithms include linear regression, decision trees, random forests, support vector machines, neural networks, and clustering algorithms like K-means."
            }
        ]
        
        # Store messages
        stored_ids = []
        for msg in messages:
            # Generate tiers
            tiers = self.tier_manager.generate_tiers(msg["content"], msg["role"])
            
            # Create message
            message_id = str(uuid.uuid4())
            message = Message(
                message_id=message_id,
                session_id=self.session_id,
                user_id=self.user_id,
                content=msg["content"],
                tier1_content=tiers["tier1_content"],
                tier2_content=tiers["tier2_content"],
                required_tier_level=1,
                role=msg["role"],
                timestamp=datetime.utcnow()
            )
            
            # Store message
            self.db.add(message)
            stored_ids.append(message_id)
        
        self.db.commit()
        
        # Build context and check that tier 1 is used by default
        context = self.context_builder.build_tiered_context(
            current_message="What's next?",
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        # Verify context structure
        self.assertIn("messages", context)
        self.assertEqual(len(context["messages"]), len(messages))
        
        # Extract the last message for testing
        last_message = self.db.query(Message)\
                         .filter_by(session_id=self.session_id)\
                         .order_by(Message.timestamp.desc())\
                         .first()
        
        # Test tier upgrade request processing
        test_response = f"Let me explain further about machine learning algorithms. [REQUEST_TIER:3:{last_message.message_id}]"
        processed = self.request_parser.process_response(test_response, self.session_id)
        
        # Verify that the response was processed correctly
        self.assertTrue(processed["need_regeneration"])
        self.assertNotIn("[REQUEST_TIER:", processed["clean_response"])
        
        # Verify tier level was updated in the database
        updated_message = self.db.query(Message)\
                            .filter_by(message_id=last_message.message_id)\
                            .first()
        self.assertEqual(updated_message.required_tier_level, 3)
        
        # Build context again and check that tier 3 is used for the last message
        updated_context = self.context_builder.build_tiered_context(
            current_message="Another question",
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        # Find the last message in the context
        last_context_message = None
        for msg in updated_context["messages"]:
            if msg.get("message_id") == last_message.message_id:
                last_context_message = msg
                break
        
        # Verify that the full content is now included
        self.assertIsNotNone(last_context_message)
        self.assertEqual(last_context_message["content"], last_message.content)
    
    def test_memory_pruning(self):
        """Test memory pruning functionality."""
        # Create a bunch of messages to exceed token limit
        for i in range(20):  # Create 20 message pairs
            # User message
            user_tiers = self.tier_manager.generate_tiers(f"User message {i}: This is a test message number {i} that contains enough text to have some tokens.", "user")
            user_msg = Message(
                message_id=f"user_{i}",
                session_id=self.session_id,
                user_id=self.user_id,
                content=f"User message {i}: This is a test message number {i} that contains enough text to have some tokens. Adding more text to increase token count significantly. The message needs to be long enough to trigger pruning when we have enough messages.",
                tier1_content=user_tiers["tier1_content"],
                tier2_content=user_tiers["tier2_content"],
                required_tier_level=1,
                role="user",
                timestamp=datetime.utcnow()
            )
            self.db.add(user_msg)
            
            # Assistant message
            assistant_tiers = self.tier_manager.generate_tiers(f"Assistant response {i}: This is a response to message {i}. It contains enough text to have a significant number of tokens.", "assistant")
            assistant_msg = Message(
                message_id=f"assistant_{i}",
                session_id=self.session_id,
                user_id=self.user_id,
                content=f"Assistant response {i}: This is a response to message {i}. It contains enough text to have a significant number of tokens. Adding more content to make it longer and increase the overall token count. We need enough total tokens to trigger pruning.",
                tier1_content=assistant_tiers["tier1_content"],
                tier2_content=assistant_tiers["tier2_content"],
                required_tier_level=1,
                role="assistant",
                timestamp=datetime.utcnow()
            )
            self.db.add(assistant_msg)
        
        self.db.commit()
        
        # Count messages before pruning
        pre_count = self.db.query(Message).filter_by(session_id=self.session_id).count()
        
        # For this test, we'll use a very small token limit to ensure pruning
        self.memory_pruner.token_limit = 1000
        
        # Perform pruning
        pruned = self.memory_pruner.check_and_prune(self.session_id, self.user_id)
        
        # Verify pruning occurred
        self.assertTrue(pruned)
        
        # Count messages after pruning
        post_count = self.db.query(Message).filter_by(session_id=self.session_id).count()
        
        # Verify message count decreased but we still have the minimum messages
        self.assertLess(post_count, pre_count)
        self.assertGreaterEqual(post_count, self.memory_pruner.min_messages)
    
    def test_episodic_memory_request(self):
        """Test episodic memory search requests."""
        # Test parsing episodic memory request
        test_response = "I need to check previous conversations. [SEARCH_EPISODIC: quantum computing]"
        processed = self.request_parser.process_response(test_response, self.session_id)
        
        # Verify response processed correctly
        self.assertTrue(processed["need_regeneration"])
        self.assertIn("episodic_query", processed)
        self.assertEqual(processed["episodic_query"], "quantum computing")
        self.assertNotIn("[SEARCH_EPISODIC:", processed["clean_response"])


if __name__ == "__main__":
    unittest.main()
