# Simple test for conversation coherence

import unittest
import logging
from datetime import datetime
import uuid
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock classes for testing
class MockMessage:
    def __init__(self, message_id, content, role, tier1="", tier2="", required_tier=1):
        self.message_id = message_id
        self.content = content
        self.tier1_content = tier1 or content[:min(20, len(content))] + "..." if len(content) > 20 else content
        self.tier2_content = tier2 or content[:min(80, len(content))] + "..." if len(content) > 80 else content
        self.required_tier_level = required_tier
        self.role = role
        self.timestamp = datetime.now()

class MockTierSystem:
    def __init__(self):
        self.messages = {}
        self.archive = []
        self.token_limit = 400  # Low for testing - ensure pruning happens
        self.current_tokens = 0
    
    def add_message(self, content, role):
        message_id = str(uuid.uuid4())
        message = MockMessage(message_id, content, role)
        self.messages[message_id] = message
        
        # Update token count (simple approximation)
        self.current_tokens += len(content) // 4
        logger.info(f"Added message with {len(content)//4} tokens, current total: {self.current_tokens}/{self.token_limit}")
        
        # Check if pruning is needed
        if self.current_tokens > self.token_limit:
            pruned = self._prune_messages()
            logger.info(f"Pruned {len(pruned)} messages. New token count: {self.current_tokens}")
        
        return message_id
    
    def _prune_messages(self):
        # Find oldest messages to prune
        sorted_ids = sorted(self.messages.keys(), key=lambda id: self.messages[id].timestamp)
        
        # Keep at least 3 messages, or prune nothing if we have 3 or fewer
        if len(sorted_ids) <= 3:
            return []
            
        to_prune = sorted_ids[:-3]  # All but the last 3 messages
        pruned = []
        
        for msg_id in to_prune:
            # Archive message
            self.archive.append(self.messages[msg_id])
            # Reduce token count
            tokens_in_msg = len(self.messages[msg_id].content) // 4
            self.current_tokens -= tokens_in_msg
            # Track pruned message
            pruned.append(msg_id)
            # Remove from active messages
            del self.messages[msg_id]
            
            # Stop if we've pruned enough
            if self.current_tokens <= self.token_limit * 0.6:  # 60% of limit
                break
                
        return pruned
    
    def request_tier_upgrade(self, message_id, tier_level):
        if message_id in self.messages:
            if tier_level > self.messages[message_id].required_tier_level:
                self.messages[message_id].required_tier_level = tier_level
                return True
        
        # Check archive
        for msg in self.archive:
            if msg.message_id == message_id:
                msg.required_tier_level = tier_level
                return True
        
        return False
    
    def search_archive(self, query):
        results = []
        for msg in self.archive:
            if query.lower() in msg.content.lower():
                results.append(msg)
        return results
    
    def get_context(self):
        result = []
        for msg_id, msg in self.messages.items():
            # Choose the right content based on tier level
            if msg.required_tier_level == 1:
                content = msg.tier1_content
            elif msg.required_tier_level == 2:
                content = msg.tier2_content
            else:
                content = msg.content
                
            result.append({
                "role": msg.role,
                "content": content,
                "message_id": msg.message_id,
                "tier": msg.required_tier_level
            })
        return result

class TestConversationCoherence(unittest.TestCase):
    def setUp(self):
        self.tier_system = MockTierSystem()
    
    def test_long_conversation_with_pruning(self):
        """Test a long conversation with pruning and tier upgrades"""
        # Create a conversation about programming languages
        conversations = [
            {
                "user": "I want to learn about programming languages.",
                "assistant": "That's a great topic! There are many programming languages, each with different strengths. Some popular ones include Python, JavaScript, Java, C++, and Ruby. What aspects interest you?"
            },
            {
                "user": "Tell me about Python specifically.",
                "assistant": "Python is a high-level, interpreted language known for its readability and simplicity. It's widely used in data science, web development, automation, and AI. Key features include dynamic typing, automatic memory management, and a vast ecosystem of libraries like NumPy, Pandas, and Django."
            },
            {
                "user": "How does JavaScript compare?",
                "assistant": "JavaScript was originally designed for web browsers, while Python is more general-purpose. JavaScript is essential for web development and runs in browsers. Both are dynamically typed, but JavaScript has more quirks. Node.js allows JavaScript to run on servers too."
            },
            {
                "user": "What about lower-level languages?",
                "assistant": "C and C++ are powerful lower-level languages offering direct memory manipulation and high performance. They require manual memory management and have a steeper learning curve than Python or JavaScript, but they're essential for system programming, game engines, and performance-critical applications."
            },
        ]
        
        # Add first batch of messages
        message_ids = []
        for convo in conversations:
            user_id = self.tier_system.add_message(convo["user"], "user")
            assistant_id = self.tier_system.add_message(convo["assistant"], "assistant")
            message_ids.append((user_id, assistant_id))
        
        # Verify context has all messages
        context = self.tier_system.get_context()
        first_context_size = len(context)
        logger.info(f"Initial context size: {first_context_size} messages")
        self.assertEqual(first_context_size, 8)  # 4 conversations × 2 messages each
        
        # Add many more messages to force pruning
        for i in range(15):  # Using more messages to ensure pruning
            user_prompt = f"Tell me about language {i+1}. This needs to be a longer message to exceed the token limit faster and ensure pruning happens during our test."
            assistant_response = f"Language {i+1} is a programming language with various features and applications in different domains. It's commonly used for tasks that require {i+1} levels of abstraction and is known for its performance in {i+1} specific areas. The syntax is based on traditional approaches but adds modern elements."
            
            self.tier_system.add_message(user_prompt, "user")
            self.tier_system.add_message(assistant_response, "assistant")
        
        # Log the states for debugging
        second_context_size = len(self.tier_system.get_context())
        archive_size = len(self.tier_system.archive)
        logger.info(f"Final context size: {second_context_size} messages")
        logger.info(f"Archive size: {archive_size} messages")
        
        # Verify pruning happened
        pruning_occurred = len(self.tier_system.archive) > 0
        self.assertTrue(pruning_occurred, f"No pruning occurred. Archive size: {archive_size}, Context size: {second_context_size}")
        
        # If pruning did not occur as expected, force a prune for testing
        if not pruning_occurred:
            logger.warning("Forcing pruning for test continuation")
            self.tier_system._prune_messages()
        
        # Request a tier upgrade for the Python message (2nd conversation)
        python_user_id, python_assistant_id = message_ids[1]
        
        # The message might be in the archive now
        found_in_messages = python_assistant_id in self.tier_system.messages
        found_in_archive = any(msg.message_id == python_assistant_id for msg in self.tier_system.archive)
        
        # Use a more informative assertion message
        self.assertTrue(found_in_messages or found_in_archive, 
                       f"Python message not found. In messages: {found_in_messages}, In archive: {found_in_archive}")
        
        # Request tier upgrade
        upgrade_success = self.tier_system.request_tier_upgrade(python_assistant_id, 3)
        self.assertTrue(upgrade_success, f"Tier upgrade failed. Message in active messages: {found_in_messages}, in archive: {found_in_archive}")
        
        # If message was archived, verify we can search for it
        if found_in_archive:
            results = self.tier_system.search_archive("Python")
            self.assertTrue(len(results) > 0, f"Failed to find Python in archived messages. Archive contains {len(self.tier_system.archive)} messages")
            
            # Look for the specific message
            found_message = None
            for msg in results:
                if msg.message_id == python_assistant_id:
                    found_message = msg
                    break
            
            self.assertIsNotNone(found_message, "Should find the specific Python message in archive")
            self.assertEqual(found_message.required_tier_level, 3, "Tier level should be upgraded to 3 even in archive")

if __name__ == "__main__":
    unittest.main()
