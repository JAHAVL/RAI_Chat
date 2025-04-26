# Test for coherence across many conversation turns

import unittest
import uuid
from datetime import datetime, timedelta
import logging
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import necessary modules - Handle both Docker and local environments
try:
    # Docker environment - modules are directly in the path
    from managers.memory.tier_manager import TierManager
    from managers.memory.context_builder import ContextBuilder
    from managers.memory.request_parser import RequestParser
    from managers.memory.memory_pruner import MemoryPruner
    from core.database.models import Message
    from core.database.connection import get_db
    logger.info("Using Docker environment imports")
except ImportError:
    try:
        # Local environment - modules are in backend package
        from backend.managers.memory.tier_manager import TierManager
        from backend.managers.memory.context_builder import ContextBuilder
        from backend.managers.memory.request_parser import RequestParser
        from backend.managers.memory.memory_pruner import MemoryPruner
        from backend.core.database.models import Message
        from backend.core.database.connection import get_db
        logger.info("Using local environment imports")
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise

class MockLLMAPI:
    def __init__(self):
        self.response_queue = []
        self.default_response = "This is a default mock response."
    
    def add_response(self, response):
        self.response_queue.append(response)
    
    def generate_response(self, prompt, system_prompt=None):
        if self.response_queue:
            return self.response_queue.pop(0)
        return self.default_response

class MockEpisodicMemory:
    def __init__(self):
        self.archived_chunks = []
    
    def archive_and_summarize_chunk(self, session_id, chunk_id, raw_chunk_data, user_id):
        self.archived_chunks.append({
            'session_id': session_id,
            'chunk_id': chunk_id,
            'data': raw_chunk_data,
            'user_id': user_id
        })
        return True
    
    def retrieve_memories(self, query, user_id, limit=5):
        # Simple mock retrieval that looks for the query in the archived chunks
        results = []
        for chunk in self.archived_chunks:
            # Check if query is in any of the messages
            for msg in chunk['data'].get('messages', []):
                if query.lower() in msg.get('content', '').lower():
                    results.append({
                        'content': msg.get('content', ''),
                        'timestamp': msg.get('timestamp', ''),
                        'relevance': 0.9  # Mock relevance score
                    })
        
        return results[:limit]

class ConversationSimulator:
    def __init__(self, db_session, token_limit=3000):
        self.user_id = "test_user"
        self.session_id = str(uuid.uuid4())
        self.db_session = db_session
        
        # Initialize components
        self.episodic_memory = MockEpisodicMemory()
        self.tier_manager = TierManager()
        self.context_builder = ContextBuilder(self.db_session)
        self.request_parser = RequestParser(self.db_session)
        self.memory_pruner = MemoryPruner(
            db_session=self.db_session,
            episodic_memory_manager=self.episodic_memory,
            token_limit=token_limit
        )
        
        # Mock LLM API
        self.llm_api = MockLLMAPI()
        
        # Track messages for verification
        self.all_messages = []  # All messages including pruned ones
        self.message_ids = []   # Just the IDs in order
        self.stored_facts = {}  # Key information mentioned in conversation
        
        # Mock tier generation
        self.tier_manager.generate_tiers = MagicMock(side_effect=self._mock_generate_tiers)
    
    def _mock_generate_tiers(self, content, role):
        """Mock tier generation for testing"""
        # Tier 1: Very concise (25% of content or first sentence)
        content_words = content.split()
        tier1_words = content_words[:max(1, len(content_words) // 4)]
        tier1 = " ".join(tier1_words)
        if len(content_words) > len(tier1_words):
            tier1 += "..."
        
        # Tier 2: Somewhat detailed (60% of content)
        tier2_words = content_words[:max(3, int(len(content_words) * 0.6))]
        tier2 = " ".join(tier2_words)
        if len(content_words) > len(tier2_words):
            tier2 += "..."
        
        return {
            "tier1_content": tier1,
            "tier2_content": tier2
        }
    
    def add_conversation_turn(self, user_input, assistant_response=None, tier_request=None, episodic_request=None):
        """Add a turn to the conversation, with optional special requests"""
        # First, store the user message
        user_message_id = self._store_user_message(user_input)
        
        # If we need to make a tier request or episodic request, modify the response
        final_response = assistant_response or self.llm_api.default_response
        
        if tier_request:
            # Add a tier request for the message ID
            target_msg_id = tier_request.get("message_id", self.message_ids[0])
            tier_level = tier_request.get("tier_level", 3)
            request_marker = f"[REQUEST_TIER:{tier_level}:{target_msg_id}] "
            final_response = request_marker + final_response
        
        if episodic_request:
            # Add an episodic memory request
            request_marker = f"[SEARCH_EPISODIC: {episodic_request}] "
            final_response = request_marker + final_response
        
        # Process the response and handle any tier/episodic requests
        processed = self.request_parser.process_response(final_response, self.session_id)
        
        # If regeneration is needed, handle it
        if processed["need_regeneration"]:
            # Handle episodic memory request if present
            episodic_context = None
            if "episodic_query" in processed:
                # Search episodic memory
                results = self.episodic_memory.retrieve_memories(
                    query=processed["episodic_query"], 
                    user_id=self.user_id
                )
                if results:
                    episodic_context = "\n".join([r.get("content", "") for r in results])
            
            # In a real system, we would regenerate the response with the new context
            # For testing, we'll just use the clean response
            final_response = processed["clean_response"]
        else:
            final_response = processed["clean_response"]
        
        # Store assistant response
        assistant_message_id = self._store_assistant_response(final_response)
        
        # Check if pruning is needed
        was_pruned = self.memory_pruner.check_and_prune(self.session_id, self.user_id)
        
        return {
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "was_pruned": was_pruned
        }
    
    def _store_user_message(self, user_input):
        """Store a user message with tiered representations"""
        # Generate tiers for the message
        tiers = self.tier_manager.generate_tiers(user_input, "user")
        
        # Create a new message
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow() - timedelta(seconds=len(self.all_messages) * 10)  # Space out timestamps
        
        message = Message(
            message_id=message_id,
            session_id=self.session_id,
            user_id=self.user_id,
            content=user_input,  # Original content (Tier 3)
            tier1_content=tiers["tier1_content"],
            tier2_content=tiers["tier2_content"],
            required_tier_level=1,  # Start with tier 1
            role="user",
            timestamp=timestamp
        )
        
        # Add to database
        self.db_session.add(message)
        self.db_session.commit()
        
        # Track this message
        self.all_messages.append({
            "id": message_id,
            "role": "user",
            "content": user_input,
            "timestamp": timestamp.isoformat()
        })
        self.message_ids.append(message_id)
        
        return message_id
    
    def _store_assistant_response(self, response_content):
        """Store an assistant response with tiered representations"""
        # Generate tiers for the message
        tiers = self.tier_manager.generate_tiers(response_content, "assistant")
        
        # Create a new message
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow() - timedelta(seconds=len(self.all_messages) * 10)  # Space out timestamps
        
        message = Message(
            message_id=message_id,
            session_id=self.session_id,
            user_id=self.user_id,
            content=response_content,  # Original content (Tier 3)
            tier1_content=tiers["tier1_content"],
            tier2_content=tiers["tier2_content"],
            required_tier_level=1,  # Start with tier 1
            role="assistant",
            timestamp=timestamp
        )
        
        # Add to database
        self.db_session.add(message)
        self.db_session.commit()
        
        # Track this message
        self.all_messages.append({
            "id": message_id,
            "role": "assistant",
            "content": response_content,
            "timestamp": timestamp.isoformat()
        })
        self.message_ids.append(message_id)
        
        return message_id
    
    def build_context(self):
        """Build the current context with proper tier levels"""
        return self.context_builder.build_tiered_context(
            current_message="",
            session_id=self.session_id,
            user_id=self.user_id
        )
    
    def get_message_by_index(self, index):
        """Get a message by its position in the conversation (0-based)"""
        if 0 <= index < len(self.message_ids):
            message_id = self.message_ids[index]
            message = self.db_session.query(Message).filter_by(message_id=message_id).first()
            return message
        return None

class TestCoherenceWithManyTurns(unittest.TestCase):
    def setUp(self):
        # Get a database session
        self.db = get_db().__enter__()
        
        # Reduce token limit for testing to force pruning
        self.token_limit = 5000
        
        # Create a simulator
        self.simulator = ConversationSimulator(
            db_session=self.db,
            token_limit=self.token_limit
        )
    
    def tearDown(self):
        # Clean up database
        try:
            self.db.query(Message).filter_by(session_id=self.simulator.session_id).delete()
            self.db.commit()
        except Exception as e:
            logger.error(f"Error during teardown: {e}")
            self.db.rollback()
        finally:
            self.db.__exit__(None, None, None)
    
    def test_long_conversation_coherence(self):
        """Test coherence in a lengthy conversation with pruning and episodic recall"""
        # Add 10 conversation turns about programming languages
        conversations = [
            # Turn 1: Introduction
            {
                "user": "Hi! I'd like to discuss programming languages today.",
                "assistant": "Hello! I'd be happy to discuss programming languages with you. What specific aspects are you interested in?"
            },
            # Turn 2: Python
            {
                "user": "Let's start with Python. What are its key features?",
                "assistant": "Python is known for its readability, simplicity, and versatility. Key features include dynamic typing, automatic memory management, and a rich ecosystem of libraries. It's widely used in data science, web development, and automation."
            },
            # Turn 3: JavaScript
            {
                "user": "How does JavaScript compare to Python?",
                "assistant": "JavaScript was designed for web browsers, while Python is more general-purpose. JavaScript is essential for web development, uses prototypal inheritance, and has asynchronous programming with Promises. Both are dynamically typed, but JavaScript has more quirks due to its design history."
            },
            # Turn 4: C++
            {
                "user": "What about C++? Is it still relevant today?",
                "assistant": "C++ remains very relevant, especially for performance-critical applications. It offers low-level memory manipulation, strong type checking, and object-oriented features. It's used in game development, embedded systems, and high-frequency trading where performance matters."
            },
            # Turn 5: Rust
            {
                "user": "I've heard Rust is a modern alternative to C++. Is that true?",
                "assistant": "Yes, Rust is often considered a modern alternative to C++. It provides memory safety guarantees without garbage collection through its ownership system. Rust prevents common memory-related bugs at compile time while offering similar performance to C++."
            },
            # Turn 6: Mobile development
            {
                "user": "Which languages are best for mobile app development?",
                "assistant": "For iOS, Swift is Apple's preferred language. For Android, Kotlin has become the recommended language over Java. For cross-platform development, options include React Native (JavaScript), Flutter (Dart), and Xamarin (C#). Each has different trade-offs between performance and development speed."
            },
            # Turn 7: Data Science
            {
                "user": "What about languages for data science?",
                "assistant": "Python dominates data science due to libraries like NumPy, Pandas, and sci-kit-learn. R is also popular, especially in statistical analysis. Julia is gaining traction for high-performance numerical computing. SQL remains essential for data manipulation, and Scala is used with Apache Spark for big data processing."
            },
            # Turn 8: Web Development
            {
                "user": "Which languages are trending in web development?",
                "assistant": "JavaScript remains the foundation of web development, with TypeScript adding static typing. Node.js enables JavaScript on the server. For frameworks, React, Vue, and Angular dominate frontend, while Express, Django (Python), Ruby on Rails, and Laravel (PHP) are popular backend choices. WebAssembly is enabling languages like Rust and C++ in browsers."
            },
            # Turn 9: Learning path
            {
                "user": "If someone is just starting programming, what should they learn first?",
                "assistant": "Python is widely recommended for beginners due to its readable syntax and gentle learning curve. JavaScript is also a good choice, especially for those interested in web development. The key is to start with a language that doesn't overwhelm beginners with complex syntax or memory management, allowing them to focus on programming concepts."
            },
            # Turn 10: Functional programming
            {
                "user": "What are functional programming languages and why are they useful?",
                "assistant": "Functional programming languages like Haskell, Clojure, and Erlang treat computation as mathematical functions, avoiding state changes and mutable data. They emphasize immutability, higher-order functions, and declarative code. Benefits include easier reasoning about programs, better concurrency support, and fewer side effects. Even mainstream languages now incorporate functional features."
            },
        ]
        
        # Add first set of turns to the conversation
        for turn in conversations:
            self.simulator.add_conversation_turn(turn["user"], turn["assistant"])
        
        # Verify the first 10 turns are in the database
        context = self.simulator.build_context()
        self.assertEqual(len(context["messages"]), 20)  # 10 turns = 20 messages
        
        # Request an upgrade to tier 3 for a message about Python (turn 2)
        python_message = self.simulator.get_message_by_index(2)  # 0-indexed
        self.simulator.add_conversation_turn(
            "Can you go into more detail about Python's use in data science?",
            "Python is the leading language in data science due to libraries like NumPy for numerical computing, Pandas for data manipulation, Matplotlib for visualization, and sci-kit-learn for machine learning. The Jupyter Notebook environment makes it ideal for exploratory data analysis and sharing results.",
            tier_request={"message_id": python_message.message_id, "tier_level": 3}
        )
        
        # Add more turns to eventually trigger pruning
        for i in range(15):
            self.simulator.add_conversation_turn(
                f"Tell me about programming language #{i+11}",
                f"This is detailed information about programming language #{i+11}. It has many features and use cases that make it suitable for certain types of development."
            )
        
        # At this point, some messages should have been pruned
        context = self.simulator.build_context()
        self.assertLess(len(context["messages"]), 52)  # 26 turns = 52 messages, should be less due to pruning
        
        # Now use episodic memory to recall information about Python
        last_turn = self.simulator.add_conversation_turn(
            "What was that about Python and data science again?",
            "Based on our earlier conversation, Python is the leading language for data science due to its extensive ecosystem of specialized libraries. NumPy provides efficient numerical arrays, Pandas offers data structures for analysis, and libraries like sci-kit-learn and TensorFlow support machine learning.",
            episodic_request="Python data science"
        )
        
        # Verify that we got search results from episodic memory
        self.assertTrue(len(self.simulator.episodic_memory.archived_chunks) > 0)
        
        # Create context and verify the Python message is properly represented
        context = self.simulator.build_context()
        
        # Verify that the upgraded Python message uses the higher tier when requested
        python_msg_in_context = None
        for msg in context["messages"]:
            if msg.get("message_id") == python_message.message_id:
                python_msg_in_context = msg
                break
        
        # If the Python message is still in context (not pruned), verify its tier level
        if python_msg_in_context is not None:
            self.assertEqual(python_msg_in_context["content"], python_message.content)  # Should use full content (tier 3)

if __name__ == "__main__":
    unittest.main()
