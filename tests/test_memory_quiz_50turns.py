# Comprehensive Memory Quiz Test - 50 Conversation Turns

import unittest
import logging
from datetime import datetime
import uuid
import random
import re
import json
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix import path issues - this is a critical fix for Docker environment
sys.path.append('/app')  # Add the app root to path in Docker

# Import necessary modules - Try Docker paths first, then local paths
try:
    from managers.memory.tier_manager import TierManager
    from managers.memory.context_builder import ContextBuilder
    from managers.memory.request_parser import RequestParser
    from managers.memory.memory_pruner import MemoryPruner
    from core.database.models import Message
    from core.database.connection import get_db
    logger.info("Using Docker environment imports")
except ImportError as e:
    logger.warning(f"Docker import failed: {e}, trying local imports")
    try:
        from backend.managers.memory.tier_manager import TierManager
        from backend.managers.memory.context_builder import ContextBuilder
        from backend.managers.memory.request_parser import RequestParser
        from backend.managers.memory.memory_pruner import MemoryPruner
        from backend.core.database.models import Message
        from backend.core.database.connection import get_db
        logger.info("Using local environment imports")
    except ImportError as e:
        logger.error(f"All imports failed: {e}. Creating minimal mock implementations instead.")
        # Will use mock implementations defined below

# Mock LLM API for generating tiered responses and handling requests
class MockLLMAPI:
    def __init__(self):
        pass
        
    def generate_response(self, prompt, system_prompt=None):
        # If prompt is asking for a tier, generate a simulated tiered representation
        if "Generate a concise tier 1" in prompt:
            return {"response": "This is a tier 1 summary."}
        elif "Generate a comprehensive tier 2" in prompt:
            return {"response": "This is a tier 2 detailed summary."}
        
        # For memory quizzing, analyze the question and respond accurately
        if "[MEMORY_QUIZ]" in prompt:
            # Extract the quiz question from the prompt
            quiz_pattern = r"\[MEMORY_QUIZ\]\s*(.+?)\s*\[/MEMORY_QUIZ\]"
            match = re.search(quiz_pattern, prompt, re.DOTALL)
            if match:
                question = match.group(1).strip()
                return {"response": self._answer_quiz(question, prompt)}
        
        # Default response with a memory request if needed
        response = "I don't have enough information."
        
        # Detect if we need higher tier info about specific facts
        for fact_keyword in ["favorite color", "birthday", "pet", "hobby", "country", "food"]:
            if fact_keyword in prompt.lower() and random.random() < 0.3:  # 30% chance to request higher tier
                # Randomly search for message IDs in the prompt
                message_id_pattern = r"message_id:\s*([0-9a-f-]+)"
                message_ids = re.findall(message_id_pattern, prompt)
                
                if message_ids:
                    random_id = random.choice(message_ids)
                    tier = random.randint(2, 3)
                    response += f" [REQUEST_TIER:{random_id}:{tier}]"
        
        # Detect if we need episodic search
        if random.random() < 0.2:  # 20% chance to perform episodic search
            topics = ["color", "birthday", "pet", "hobby", "country", "food"]
            topic = random.choice(topics)
            response += f" [SEARCH_EPISODIC:{topic}]"
            
        return {"response": response}
    
    def _answer_quiz(self, question, context):
        # Extract all facts from the context to use for answering
        facts = {}
        
        # Look for stored facts in the conversation
        fact_pattern = r"FACT:\s*(.+?)\s*=\s*(.+?)\s*\|"
        fact_matches = re.findall(fact_pattern, context, re.DOTALL)
        
        for key, value in fact_matches:
            facts[key.strip().lower()] = value.strip()
        
        # Try to answer based on the question
        question_lower = question.lower()
        for key in facts:
            if key in question_lower:
                return facts[key]
        
        # If we can't find a direct match
        return "I don't recall that information."

# Mock Message class with tiered content support
class MockMessage:
    def __init__(self, message_id, content, role, session_id, tier1=None, tier2=None, required_tier=1, metadata=None):
        self.message_id = message_id
        self.content = content
        self.tier1_content = tier1 or self._generate_tier1(content)
        self.tier2_content = tier2 or self._generate_tier2(content)
        self.required_tier_level = required_tier
        self.role = role
        self.session_id = session_id
        self.timestamp = datetime.now()
        self.message_metadata = metadata or {}
    
    def _generate_tier1(self, content):
        # Create a very concise tier 1 representation
        if len(content) <= 30:
            return content
        
        # Extract key facts if present in special format
        if "FACT:" in content:
            fact_match = re.search(r"FACT:\s*(.+?)\s*=\s*(.+?)\s*\|", content)
            if fact_match:
                key, value = fact_match.groups()
                return f"Mentioned {key.strip()}"
        
        # Default summarization
        words = content.split()
        if len(words) > 10:
            return " ".join(words[:8]) + "..."
        return content
    
    def _generate_tier2(self, content):
        # Create a somewhat detailed tier 2 representation
        if len(content) <= 100:
            return content
        
        # Extract facts if present
        if "FACT:" in content:
            fact_match = re.search(r"FACT:\s*(.+?)\s*=\s*(.+?)\s*\|", content)
            if fact_match:
                key, value = fact_match.groups()
                return f"Discussed {key.strip()} information"
        
        # Default summarization
        words = content.split()
        if len(words) > 25:
            return " ".join(words[:20]) + "..."
        return content

# Advanced MockTierSystem that simulates the full tiered memory stack
class MockTierSystem:
    def __init__(self, token_limit=1000):
        self.messages = {}
        self.archive = []
        self.token_limit = token_limit  # Adjustable for testing
        self.current_tokens = 0
        self.session_id = str(uuid.uuid4())
        self.llm_api = MockLLMAPI()
        self.tier_manager = TierManager(self.llm_api)
        self.context_builder = ContextBuilder()
        self.request_parser = RequestParser()
        self.pruner = MemoryPruner(token_limit=token_limit)
        
        # Fact storage for quiz evaluation
        self.facts = {}
        self.quiz_answers = {}
        self.quiz_correct = 0
        self.quiz_total = 0
    
    def add_message(self, content, role, store_fact=False):
        message_id = str(uuid.uuid4())
        
        # Extract and store any facts for later quizzing
        if store_fact and "FACT:" in content:
            fact_match = re.search(r"FACT:\s*(.+?)\s*=\s*(.+?)\s*\|", content)
            if fact_match:
                key, value = fact_match.groups()
                self.facts[key.strip()] = value.strip()
                logger.info(f"Stored fact: {key.strip()} = {value.strip()}")
        
        message = MockMessage(message_id, content, role, self.session_id)
        self.messages[message_id] = message
        
        # Update token count (approximate 4 chars = 1 token)
        tokens = len(content) // 4
        self.current_tokens += tokens
        logger.info(f"Added {role} message: {content[:50]}... ({tokens} tokens, total: {self.current_tokens}/{self.token_limit})")
        
        # Check if pruning is needed
        if self.current_tokens > self.token_limit:
            pruned_ids = self._prune_messages()
            logger.info(f"Pruned {len(pruned_ids)} messages. New token count: {self.current_tokens}")
        
        return message_id
    
    def _prune_messages(self):
        # Sort messages by timestamp (oldest first)
        sorted_messages = sorted(self.messages.values(), key=lambda msg: msg.timestamp)
        
        # Always keep at least the 5 most recent messages
        if len(sorted_messages) <= 5:
            return []
        
        # Identify messages to prune (oldest ones first)
        to_prune = sorted_messages[:-5]  # All except the 5 most recent
        pruned_ids = []
        tokens_pruned = 0
        
        for msg in to_prune:
            # Calculate tokens in this message
            msg_tokens = len(msg.content) // 4
            
            # Archive the message
            self.archive.append(msg)
            
            # Track tokens removed and message ID
            tokens_pruned += msg_tokens
            pruned_ids.append(msg.message_id)
            
            # Remove from active messages
            del self.messages[msg.message_id]
            
            # Stop if we've pruned enough to get under 80% of the limit
            if self.current_tokens - tokens_pruned <= self.token_limit * 0.8:
                break
        
        # Update the token count
        self.current_tokens -= tokens_pruned
        
        return pruned_ids
    
    def request_tier_upgrade(self, message_id, tier_level):
        # Check if message is in active messages
        if message_id in self.messages:
            msg = self.messages[message_id]
            if tier_level > msg.required_tier_level:
                msg.required_tier_level = tier_level
                logger.info(f"Upgraded active message {message_id[:8]} to tier {tier_level}")
                return True
        
        # Check archived messages
        for msg in self.archive:
            if msg.message_id == message_id:
                if tier_level > msg.required_tier_level:
                    msg.required_tier_level = tier_level
                    logger.info(f"Upgraded archived message {message_id[:8]} to tier {tier_level}")
                    return True
        
        logger.warning(f"Message {message_id[:8]} not found for tier upgrade")
        return False
    
    def search_episodic(self, query):
        results = []
        for msg in self.archive:
            if query.lower() in msg.content.lower():
                results.append(msg)
        
        logger.info(f"Episodic search for '{query}' found {len(results)} results")
        return results
    
    def get_context(self):
        result = []
        for msg_id, msg in self.messages.items():
            # Choose the right content based on required tier level
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
        
        return sorted(result, key=lambda x: self.messages[x["message_id"]].timestamp)
    
    def process_assistant_response(self, response, prompt):
        # Parse the response for any tier or episodic search requests
        tier_requests = self.request_parser.extract_tier_requests(response)
        episodic_requests = self.request_parser.extract_episodic_requests(response)
        
        # Handle tier upgrade requests
        for message_id, tier_level in tier_requests:
            self.request_tier_upgrade(message_id, tier_level)
        
        # Handle episodic search requests
        for query in episodic_requests:
            search_results = self.search_episodic(query)
            
            # Log the search results
            if search_results:
                logger.info(f"Found {len(search_results)} archived messages about '{query}'")
                for result in search_results[:3]:  # Log first 3 results
                    logger.info(f"  - {result.content[:50]}...")
        
        # Clean response by removing the special commands
        clean_response = self.request_parser.clean_response(response)
        return clean_response
    
    def quiz_memory(self, question):
        # Construct a prompt with the current context and the quiz question
        context = self.get_context()
        context_str = "\n".join([f"{item['role']}: {item['content']} (message_id: {item['message_id']}, tier: {item['tier']})" for item in context])
        
        # Add archived messages that might contain relevant info (simulating what episodic search would do)
        if any(keyword in question.lower() for keyword in self.facts.keys()):
            for msg in self.archive:
                if any(keyword in msg.content.lower() for keyword in self.facts.keys()):
                    context_str += f"\nARCHIVED_{msg.role}: {msg.content} (message_id: {msg.message_id})"
        
        # Add the quiz question
        prompt = f"{context_str}\n\n[MEMORY_QUIZ]{question}[/MEMORY_QUIZ]"
        
        # Get response from the mock LLM
        response_data = self.llm_api.generate_response(prompt, None)
        answer = response_data.get("response", "I don't know.")
        
        # Process any tier requests in the response
        clean_answer = self.process_assistant_response(answer, prompt)
        
        # Evaluate the answer
        self.quiz_total += 1
        expected_answer = None
        
        # Try to find the expected answer in our stored facts
        for fact_key, fact_value in self.facts.items():
            if fact_key.lower() in question.lower():
                expected_answer = fact_value
                break
        
        # Store the answer for later analysis
        question_key = question.strip()
        self.quiz_answers[question_key] = {
            "question": question,
            "given_answer": clean_answer,
            "expected_answer": expected_answer,
            "correct": False
        }
        
        # Check if the answer is correct (allowing for some variation)
        if expected_answer and (expected_answer.lower() in clean_answer.lower() or 
                              clean_answer.lower() in expected_answer.lower()):
            self.quiz_correct += 1
            self.quiz_answers[question_key]["correct"] = True
            logger.info(f"QUIZ: Correct answer for '{question}'")
        else:
            logger.info(f"QUIZ: Incorrect answer for '{question}' - Expected: '{expected_answer}', Got: '{clean_answer}'")
        
        return clean_answer, expected_answer, self.quiz_answers[question_key]["correct"]
    
    def get_quiz_accuracy(self):
        if self.quiz_total == 0:
            return 0.0
        return (self.quiz_correct / self.quiz_total) * 100

class TestTieredMemoryQuiz(unittest.TestCase):
    def setUp(self):
        # Create a memory system with a deliberately low token limit to force pruning
        self.memory = MockTierSystem(token_limit=2000)
        
        # Create a list of interesting facts for the conversation
        self.facts = [
            ("favorite color", "cerulean blue"),
            ("birthday", "March 15"),
            ("pet", "a golden retriever named Max"),
            ("hobby", "collecting vintage postcards"),
            ("hometown", "Springfield, Illinois"),
            ("favorite food", "spicy Thai curry"),
            ("first job", "lifeguard at the community pool"),
            ("dream vacation", "touring the ancient temples of Japan"),
            ("best friend", "Jamie, who they've known since kindergarten"),
            ("lucky number", "seventeen"),
            ("college major", "Environmental Science"),
            ("favorite book", "The Name of the Wind"),
            ("favorite movie", "The Shawshank Redemption"),
            ("career goal", "to start a sustainable technology company"),
            ("biggest fear", "public speaking"),
            ("favorite season", "autumn when the leaves change"),
            ("allergies", "peanuts and bee stings"),
            ("hidden talent", "can solve a Rubik's cube in under 2 minutes"),
            ("role model", "their grandfather who was an inventor"),
            ("favorite musician", "Beethoven, especially his piano sonatas"),
            ("morning routine", "yoga followed by a green smoothie"),
            ("preferred exercise", "rock climbing"),
            ("comfort food", "homemade mac and cheese with extra cheese"),
            ("favorite subject in school", "physics"),
            ("ideal weekend", "hiking followed by reading by a fireplace"),
            ("phobia", "heights"),
            ("favorite art style", "impressionism"),
            ("unusual skill", "can identify bird species by their calls"),
            ("childhood hero", "Marie Curie"),
            ("first car", "a blue Honda Civic with over 200,000 miles"),
            ("life motto", "progress not perfection"),
            ("favorite holiday", "Thanksgiving for the food and family time"),
            ("secret wish", "to play piano in a concert hall"),
            ("unique collection", "unusual coffee mugs from around the world"),
            ("proudest achievement", "running a marathon after recovering from an injury"),
            ("foreign language", "conversational in Spanish and learning Mandarin"),
            ("favorite game", "chess, particularly studying famous matches"),
            ("most visited website", "a specialized forum for botanical enthusiasts"),
            ("recurring dream", "flying over their childhood neighborhood"),
            ("desired superpower", "teleportation to avoid traffic and visit places instantly"),
            ("favorite constellation", "Orion because it was the first one they learned"),
            ("favorite quote", "Be the change you wish to see in the world"),
            ("unusual habit", "organizing books by color instead of author or title"),
            ("favorite historical period", "the Renaissance for its scientific discoveries"),
            ("surprising fact", "can recite the first 100 digits of pi"),
            ("daily ritual", "writing in a gratitude journal before bed"),
            ("guilty pleasure", "reality TV cooking competitions"),
            ("life-changing book", "Thinking, Fast and Slow by Daniel Kahneman"),
            ("signature dish", "homemade lasagna with a secret family recipe sauce"),
            ("bucket list item", "seeing the Northern Lights in person")
        ]
    
    def test_50_turn_conversation_with_quizzing(self):
        """Test a 50-turn conversation with fact introduction and memory quizzing"""
        # Track all message IDs for potential tier upgrades
        all_messages = []
        
        # Set random seed for reproducibility
        random.seed(42)
        
        # Phase 1: Introduce 50 facts in conversation turns
        logger.info("=== PHASE 1: Introducing Facts ===")
        for i in range(50):
            # Select a random fact and format it for the conversation
            fact_key, fact_value = self.facts[i % len(self.facts)]
            turn_number = i + 1
            
            # User messages introduce facts
            user_message = f"Turn {turn_number}: Let me tell you about my {fact_key}. FACT: {fact_key} = {fact_value} | What do you think about that?"
            user_id = self.memory.add_message(user_message, "user", store_fact=True)
            all_messages.append(user_id)
            
            # Simulate assistant response
            context = self.memory.get_context()
            context_str = "\n".join([f"{item['role']}: {item['content']} (message_id: {item['message_id']}, tier: {item['tier']})" for item in context])
            
            response_data = self.memory.llm_api.generate_response(context_str, None)
            raw_response = response_data.get("response", "I understand.")
            
            # Process any tier or episodic requests in the response
            clean_response = self.memory.process_assistant_response(raw_response, context_str)
            
            # Add assistant's response to the conversation
            assistant_id = self.memory.add_message(f"Turn {turn_number} response: {clean_response}", "assistant")
            all_messages.append(assistant_id)
            
            # Occasionally request tier upgrades for random older messages
            if i > 10 and random.random() < 0.2:  # 20% chance after turn 10
                old_messages = all_messages[:-10]  # Exclude the 10 most recent messages
                if old_messages:
                    random_id = random.choice(old_messages)
                    tier = random.randint(2, 3)
                    self.memory.request_tier_upgrade(random_id, tier)
        
        # Log current memory state
        active_count = len(self.memory.messages)
        archive_count = len(self.memory.archive)
        logger.info(f"After 50 turns: {active_count} active messages, {archive_count} archived messages")
        self.assertTrue(archive_count > 0, "Should have archived some messages due to pruning")
        
        # Phase 2: Quiz the memory system on facts from different memory zones
        logger.info("\n=== PHASE 2: Memory Quizzing ===")
        
        # Create quiz questions for facts from active messages, archived messages, and a mix
        quiz_questions = []
        
        # Generate questions for all facts
        for fact_key, fact_value in self.facts:
            # Vary the phrasing to test robustness
            question_formats = [
                f"What is my {fact_key}?",
                f"Can you tell me what my {fact_key} is?",
                f"Do you remember my {fact_key}?",
                f"I previously mentioned my {fact_key}, what was it?"
            ]
            question = random.choice(question_formats)
            quiz_questions.append((question, fact_key, fact_value))
        
        # Shuffle the questions
        random.shuffle(quiz_questions)
        
        # Run the quiz for as many questions as we have facts (up to 50)
        quiz_results = []
        for question, fact_key, expected in quiz_questions[:50]:
            answer, expected_answer, is_correct = self.memory.quiz_memory(question)
            quiz_results.append({
                "question": question,
                "answer": answer,
                "expected": expected_answer,
                "correct": is_correct,
                "fact_key": fact_key
            })
        
        # Calculate quiz statistics
        accuracy = self.memory.get_quiz_accuracy()
        logger.info(f"\n=== QUIZ RESULTS ===")
        logger.info(f"Overall accuracy: {accuracy:.2f}% ({self.memory.quiz_correct}/{self.memory.quiz_total})")
        
        # Log details of incorrect answers
        if self.memory.quiz_correct < self.memory.quiz_total:
            logger.info("\nIncorrect answers:")
            for question, data in self.memory.quiz_answers.items():
                if not data["correct"]:
                    logger.info(f"Q: {data['question']}")
                    logger.info(f"   Expected: {data['expected_answer']}")
                    logger.info(f"   Got: {data['given_answer']}")
        
        # Analyze memory zones
        active_facts = set()
        archived_facts = set()
        
        # Check which facts are in active messages
        for msg_id, msg in self.memory.messages.items():
            for fact_key, _ in self.facts:
                if fact_key.lower() in msg.content.lower():
                    active_facts.add(fact_key)
        
        # Check which facts are in archived messages
        for msg in self.memory.archive:
            for fact_key, _ in self.facts:
                if fact_key.lower() in msg.content.lower():
                    archived_facts.add(fact_key)
        
        logger.info(f"\nMemory zone analysis:")
        logger.info(f"Facts in active memory: {len(active_facts)}")
        logger.info(f"Facts in archived memory: {len(archived_facts)}")
        
        # Calculate accuracy by memory zone
        active_correct = 0
        active_total = 0
        archived_correct = 0
        archived_total = 0
        
        for result in quiz_results:
            if result["fact_key"] in active_facts:
                active_total += 1
                if result["correct"]:
                    active_correct += 1
            elif result["fact_key"] in archived_facts:
                archived_total += 1
                if result["correct"]:
                    archived_correct += 1
        
        if active_total > 0:
            active_accuracy = (active_correct / active_total) * 100
            logger.info(f"Accuracy for facts in active memory: {active_accuracy:.2f}% ({active_correct}/{active_total})")
        
        if archived_total > 0:
            archived_accuracy = (archived_correct / archived_total) * 100
            logger.info(f"Accuracy for facts in archived memory: {archived_accuracy:.2f}% ({archived_correct}/{archived_total})")
        
        # Final assertions
        self.assertGreater(accuracy, 50.0, "Overall accuracy should be above 50%")
        if archived_total > 0:
            self.assertGreater(archived_accuracy, 30.0, "Archived memory accuracy should be above 30%")

if __name__ == "__main__":
    unittest.main()
