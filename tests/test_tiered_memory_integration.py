# RAI_Chat/tests/test_tiered_memory_integration.py

import sys
import os
import logging
import unittest
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
sys.path.append(project_dir)

# Set up MySQL environment variables for testing (using Docker MySQL container)
os.environ['MYSQL_HOST'] = 'localhost'  # Connect to local port forwarded from Docker
os.environ['MYSQL_PORT'] = '3307'  # The mapped port from docker-compose
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = 'root'  # Default password in Docker environment
os.environ['MYSQL_DATABASE'] = 'rai_chat'

# Import the necessary modules
from backend.managers.memory.tier_manager import TierManager
from backend.managers.memory.context_builder import ContextBuilder
from backend.managers.memory.request_parser import RequestParser
from backend.managers.memory.memory_pruner import MemoryPruner
from backend.core.database.models import Message, Base
from backend.core.database.connection import get_database_url, create_db_engine

# Create a test engine with MySQL
test_db_url = get_database_url()
test_engine = create_db_engine(test_db_url)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Define mock LLM API for testing
class MockLLMAPI:
    def __init__(self):
        self.response_queue = []
    
    def add_response(self, response):
        self.response_queue.append(response)
    
    def generate_response(self, prompt, system_prompt=None):
        if not self.response_queue:
            return "Default mock response"
        return self.response_queue.pop(0)
    
    def generate_chat_completion(self, messages, model=None, stream=False):
        if not self.response_queue:
            return "Default mock response"
        return self.response_queue.pop(0)

# Mock the ConversationManager for testing
class MockConversationManager:
    def __init__(self, user_id, session_id=None, db_session=None):
        self.user_id = user_id
        self.current_session_id = session_id or str(uuid.uuid4())
        self.logger = logging.getLogger(f"MockConvMgr_User{self.user_id}")
        
        # Get database session (passed in, not created here)
        self.db_session = db_session
        
        # Initialize the tiered memory components
        self.tier_manager = TierManager()
        self.context_builder = ContextBuilder(self.db_session)
        self.request_parser = RequestParser(self.db_session)
        self.memory_pruner = MemoryPruner(
            db_session=self.db_session,
            episodic_memory_manager=None,
            token_limit=5000
        )
        
        # Mock LLM API
        self.llm_api = MockLLMAPI()
    
    def process_tiered_message(self, user_input):
        # Store the user message
        user_message_id = self._store_user_message(user_input)
        
        # Build context
        context = self.context_builder.build_tiered_context(
            current_message=user_input,
            session_id=self.current_session_id,
            user_id=self.user_id
        )
        
        # Get response from LLM
        response = self.llm_api.generate_response(user_input, "System prompt")
        
        # Check for tier requests or episodic memory requests
        processed = self.request_parser.process_response(response, self.current_session_id)
        
        # If regeneration is needed, handle it
        if processed["need_regeneration"]:
            # Handle episodic memory request if present
            episodic_context = None
            if "episodic_query" in processed:
                # Search episodic memory (mocked)
                episodic_context = f"Mocked episodic content for query: {processed['episodic_query']}"
            
            # Regenerate response
            response = self.llm_api.generate_response(user_input, "Updated system prompt")
            processed = self.request_parser.process_response(response, self.current_session_id)
        
        # Store assistant response
        self._store_assistant_response(processed["clean_response"])
        
        # Yield the response
        yield {
            'type': 'content',
            'content': processed["clean_response"],
            'timestamp': datetime.now().isoformat(),
            'session_id': self.current_session_id
        }
    
    def _store_user_message(self, user_input):
        # Generate tiers
        tiers = self.tier_manager.generate_tiers(user_input, "user")
        
        # Create message
        message_id = str(uuid.uuid4())
        message = Message(
            message_id=message_id,
            session_id=self.current_session_id,
            user_id=self.user_id,
            content=user_input,
            tier1_content=tiers["tier1_content"],
            tier2_content=tiers["tier2_content"],
            required_tier_level=1,
            role="user",
            timestamp=datetime.utcnow()
        )
        
        # Store in database
        self.db_session.add(message)
        self.db_session.commit()
        return message_id
    
    def _store_assistant_response(self, response_content):
        # Generate tiers
        tiers = self.tier_manager.generate_tiers(response_content, "assistant")
        
        # Create message
        message_id = str(uuid.uuid4())
        message = Message(
            message_id=message_id,
            session_id=self.current_session_id,
            user_id=self.user_id,
            content=response_content,
            tier1_content=tiers["tier1_content"],
            tier2_content=tiers["tier2_content"],
            required_tier_level=1,
            role="assistant",
            timestamp=datetime.utcnow()
        )
        
        # Store in database
        self.db_session.add(message)
        self.db_session.commit()
        return message_id

class TestTieredMemoryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Create necessary tables if they don't exist
        try:
            Base.metadata.create_all(bind=test_engine)
            logger.info("Test database tables created or verified")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def setUp(self):
        """Set up fresh database and components for each test"""
        # Create a new session for each test
        self.db = TestSessionLocal()
        self.user_id = "test_user"
        self.session_id = str(uuid.uuid4())
        
        # Initialize tier manager with mocked generation
        self.tier_manager = TierManager()
        
        # Add mock tier generation behavior
        def mock_generate_tiers(content, role):
            tier1 = content[:30] + "..." if len(content) > 30 else content
            tier2 = content[:100] + "..." if len(content) > 100 else content
            return {"tier1_content": tier1, "tier2_content": tier2}
        
        self.tier_manager.generate_tiers = MagicMock(side_effect=mock_generate_tiers)
        
        # Initialize with clean database for each test
        try:
            self.db.query(Message).filter_by(session_id=self.session_id).delete()
            self.db.commit()
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
            self.db.rollback()
    
    def tearDown(self):
        # Clean up database
        try:
            self.db.query(Message).filter_by(session_id=self.session_id).delete()
            self.db.commit()
        except Exception as e:
            logger.error(f"Error during teardown: {e}")
            self.db.rollback()
        finally:
            self.db.close()
    
    @patch('backend.managers.memory.tier_manager.get_llm_api')
    def test_conversation_with_tier_request(self, mock_get_llm_api):
        """Test a conversation flow with tier request"""
        # Mock the LLM API access
        mock_llm_api = MockLLMAPI()
        mock_get_llm_api.return_value = mock_llm_api
        
        # Create conversation manager with mocked components
        conversation_manager = MockConversationManager(user_id=self.user_id, session_id=self.session_id, db_session=self.db)
        conversation_manager.tier_manager = self.tier_manager
        
        # First message from user
        user_message = "Can you explain the difference between supervised and unsupervised learning?"
        
        # Set up mock LLM response without tier request
        initial_response = "Supervised learning uses labeled data for training, while unsupervised learning works with unlabeled data."
        conversation_manager.llm_api.add_response(initial_response)
        
        # Process the first message
        first_response_chunks = list(conversation_manager.process_tiered_message(user_message))
        
        # Verify first response
        self.assertEqual(len(first_response_chunks), 1)
        self.assertEqual(first_response_chunks[0]['type'], 'content')
        self.assertEqual(first_response_chunks[0]['content'], initial_response)
        
        # Second message from user
        second_user_message = "What are some common algorithms for each type?"
        
        # Set up mock LLM response with a tier request
        # The LLM is requesting more context about the first message
        first_message = self.db.query(Message).filter_by(role="user", session_id=self.session_id).first()
        if not first_message:
            self.fail("First message not found in database")
            
        response_with_tier_request = f"[REQUEST_TIER:3:{first_message.message_id}] Based on your question about machine learning paradigms, common supervised learning algorithms include Linear Regression, Decision Trees, and Support Vector Machines."
        expected_clean_response = "Based on your question about machine learning paradigms, common supervised learning algorithms include Linear Regression, Decision Trees, and Support Vector Machines."
        
        # Add two responses because the first one will trigger regeneration
        conversation_manager.llm_api.add_response(response_with_tier_request)
        conversation_manager.llm_api.add_response(expected_clean_response)
        
        # Process the second message
        second_response_chunks = list(conversation_manager.process_tiered_message(second_user_message))
        
        # Verify second response
        self.assertEqual(len(second_response_chunks), 1)
        self.assertEqual(second_response_chunks[0]['type'], 'content')
        self.assertEqual(second_response_chunks[0]['content'], expected_clean_response)
        
        # Verify the first message's tier level was upgraded
        updated_first_message = self.db.query(Message).filter_by(message_id=first_message.message_id).first()
        self.assertEqual(updated_first_message.required_tier_level, 3)
        
        # Third message to verify the context now includes full content for the first message
        third_user_message = "Can you also explain ensemble methods?"
        
        # Check that context builder will use the correct tier level
        context = conversation_manager.context_builder.build_tiered_context(
            current_message=third_user_message,
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        # Find the first user message in the context
        first_message_in_context = None
        for msg in context['messages']:
            if msg.get('message_id') == first_message.message_id:
                first_message_in_context = msg
                break
        
        # Verify the message uses the full content (tier 3)
        self.assertIsNotNone(first_message_in_context)
        self.assertEqual(first_message_in_context['content'], first_message.content)
    
    @patch('backend.managers.memory.tier_manager.get_llm_api')
    def test_conversation_with_episodic_request(self, mock_get_llm_api):
        """Test a conversation flow with episodic memory request"""
        # Mock the LLM API access
        mock_llm_api = MockLLMAPI()
        mock_get_llm_api.return_value = mock_llm_api
        
        # Create conversation manager with mocked components
        conversation_manager = MockConversationManager(user_id=self.user_id, session_id=self.session_id, db_session=self.db)
        conversation_manager.tier_manager = self.tier_manager
        
        # First message from user
        user_message = "Tell me about neural networks"
        
        # Set up mock LLM response with episodic memory request
        response_with_episodic = "I need to check our previous conversations about this topic. [SEARCH_EPISODIC: neural networks]"
        expected_final_response = "Based on our previous discussions, neural networks are computational models inspired by the human brain."
        
        # Add responses to the queue
        conversation_manager.llm_api.add_response(response_with_episodic)
        conversation_manager.llm_api.add_response(expected_final_response)
        
        # Process the message
        response_chunks = list(conversation_manager.process_tiered_message(user_message))
        
        # Verify response
        self.assertEqual(len(response_chunks), 1)
        self.assertEqual(response_chunks[0]['type'], 'content')
        self.assertEqual(response_chunks[0]['content'], expected_final_response)

if __name__ == "__main__":
    unittest.main()
