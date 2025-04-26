"""
RAI_Chat/Backend/managers/conversation_manager.py
Refactored conversation manager using modular components for the RAI Chat application
"""

import json
import os
import re
import requests
import logging
import importlib.util
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Generator, Tuple, Union
from sqlalchemy.orm import Session as SQLAlchemySession

# Import database connection
from models.connection import get_db

# Import other managers and components
from managers.memory.contextual_memory import ContextualMemoryManager
from managers.memory.episodic_memory import EpisodicMemoryManager
from managers.memory.memory_importance_scorer import MemoryImportanceScorer
from managers.chat_file_manager import ChatFileManager
from components.prompt_builder import PromptBuilder
from components.action_handler import ActionHandler, ACTION_COMMAND_DETECTED
from utils.pathconfig import ensure_directory_exists

# Import our refactored components
from managers.conversation.search_handler import SearchHandler
from managers.conversation.context_builder import ContextBuilder
from managers.conversation.response_processor import ResponseProcessor

# Set up logging
logger = logging.getLogger(__name__)

# Define constants
LOGS_DIR = os.path.join('/app', 'data', 'logs')
ensure_directory_exists(LOGS_DIR)
os.makedirs(LOGS_DIR, exist_ok=True)

# Set the LLM Engine path
llm_engine_path = "/app/llm_client"
logger.info(f"LLM Engine path: {llm_engine_path}")

# Define fallback functions in case LLM client import fails
def get_llm_api():
    """Fallback function that returns a simple LLM API client."""
    logger.warning("Using fallback LLM API client")
    
    class FallbackLLMAPI:
        def generate_response(self, prompt, system_prompt=None):
            return {"response": "LLM API not available. This is a fallback response."}
    
    return FallbackLLMAPI()

def get_llm_engine():
    """Fallback function that returns a simple LLM Engine."""
    logger.warning("Using fallback LLM Engine")
    
    class FallbackLLMEngine:
        def generate(self, prompt, system_prompt=None):
            return "LLM Engine not available. This is a fallback response."
    
    return FallbackLLMEngine()

# Try to import the real LLM client
try:
    # In Docker, we use a simple HTTP client to communicate with the LLM Engine
    class DockerLLMAPI:
        def __init__(self):
            self.llm_api_url = os.environ.get('LLM_API_URL', 'http://rai-llm-engine:6101')
            logger.info(f"Initializing Docker LLM API client with URL: {self.llm_api_url}")
        
        def generate_response(self, prompt, system_prompt=None):
            """Generate a response from the LLM Engine."""
            try:
                # Prepare the request data
                data = {
                    "prompt": prompt,
                    "system_prompt": system_prompt or ""
                }
                
                # Send the request to the LLM Engine
                response = requests.post(f"{self.llm_api_url}/api/generate", json=data)
                
                # Check if the request was successful
                if response.status_code == 200:
                    response_data = response.json()
                    # Add debug logging
                    logger.info(f"LLM API raw response: {str(response_data)[:200]}...")
                    logger.info(f"LLM API response type: {type(response_data)}")
                    if isinstance(response_data, dict):
                        logger.info(f"LLM API response keys: {list(response_data.keys())}")
                    return response_data
                else:
                    logger.error(f"LLM API request failed with status code: {response.status_code}")
                    return {"response": f"Error: LLM API request failed with status code {response.status_code}"}
            
            except Exception as e:
                logger.error(f"Error generating response from LLM API: {str(e)}")
                return {"response": f"Error: {str(e)}"}
        
        def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1000):
            """Alias for generate_response with additional parameters for compatibility."""
            return self.generate_response(prompt, system_prompt)
        
        def generate_text(self, prompt, temperature=0.7, max_tokens=1000):
            """Generate text without a system prompt - for memory extraction."""
            response_data = self.generate_response(prompt)
            if isinstance(response_data, dict) and "response" in response_data:
                return response_data["response"]
            elif isinstance(response_data, str):
                return response_data
            else:
                # Try to extract the response from a nested structure
                try:
                    if "text" in response_data:
                        return response_data["text"]
                    else:
                        return str(response_data)
                except Exception as e:
                    logger.error(f"Error extracting text from response: {str(e)}")
                    return "Error generating text"
        
        def chat_completion(self, messages, temperature=0.7, max_tokens=1000, session_id=None):
            """
            Process a chat completion request - for memory extraction.
            For compatibility with the expected format in contextual_memory.py
            """
            try:
                # Combine messages into a prompt for the LLM Engine
                prompt = ""
                system_prompt = ""
                
                for message in messages:
                    role = message.get("role", "").lower()
                    content = message.get("content", "")
                    
                    if role == "system":
                        system_prompt += content + "\n"
                    elif role == "user":
                        prompt += f"User: {content}\n"
                    elif role == "assistant":
                        prompt += f"Assistant: {content}\n"
                    else:
                        prompt += f"{role.capitalize()}: {content}\n"
                
                # Remove trailing newline
                prompt = prompt.strip()
                system_prompt = system_prompt.strip()
                
                # Generate response
                response_data = self.generate_response(prompt, system_prompt)
                
                # Extract the content from the response
                content = self._extract_content_from_response(response_data)
                
                # Return in a format compatible with chat completion
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": content
                            }
                        }
                    ]
                }
                
            except Exception as e:
                logger.error(f"Error processing chat completion: {str(e)}")
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": f"Error: {str(e)}"
                            }
                        }
                    ]
                }
        
        def _extract_content_from_response(self, response_data):
            """
            Extract content from various response formats.
            Handles different response structures from the LLM API.
            """
            try:
                content = ""
                
                # Handle different response formats
                if isinstance(response_data, str):
                    # Direct string response
                    content = response_data
                elif isinstance(response_data, dict):
                    # Dictionary response - try different keys
                    if "response" in response_data:
                        # This is the format returned by DockerLLMAPI
                        content = response_data["response"]
                    elif "text" in response_data:
                        # This is the format returned by DockerLLMAPI - text might contain
                        # markdown code blocks with JSON inside
                        text_content = response_data["text"]
                        
                        # Check if the text contains markdown code blocks with JSON
                        if text_content and '```json' in text_content:
                            logger.info("Found markdown JSON block in response, attempting to extract tier3 content")
                            import re
                            import json
                            
                            # Extract the JSON content from markdown code blocks
                            json_match = re.search(r'```json\s*\n(.*?)\n\s*```', text_content, re.DOTALL)
                            if json_match:
                                try:
                                    json_str = json_match.group(1)
                                    parsed_json = json.loads(json_str)
                                    logger.info(f"Successfully parsed JSON from markdown block, keys: {list(parsed_json.keys())}")
                                    
                                    # Extract tier3 content from the parsed JSON
                                    if "llm_response" in parsed_json:
                                        if "response_tiers" in parsed_json["llm_response"]:
                                            tier3 = parsed_json["llm_response"]["response_tiers"].get("tier3", "")
                                            if tier3:
                                                logger.info(f"Successfully extracted tier3 content: {tier3[:100]}...")
                                                content = tier3
                                            else:
                                                content = text_content
                                        else:
                                            content = parsed_json["llm_response"]
                                    else:
                                        content = text_content
                                except json.JSONDecodeError as e:
                                    logger.error(f"Failed to parse JSON from markdown block: {e}")
                                    content = text_content
                            else:
                                content = text_content
                        else:
                            content = text_content
                    elif "content" in response_data:
                        content = response_data["content"]
                    elif "message" in response_data:
                        if isinstance(response_data["message"], dict) and "content" in response_data["message"]:
                            content = response_data["message"]["content"]
                        else:
                            content = str(response_data["message"])
                    elif "answer" in response_data:
                        content = response_data["answer"]
                    elif len(response_data) > 0:
                        # Just take the first key's value
                        first_key = list(response_data.keys())[0]
                        content = str(response_data[first_key])
                        logger.info(f"Using first key {first_key} for content")
                else:
                    # For any other type, convert to string
                    content = str(response_data)
                    
                # Make sure we actually have some content
                if not content:
                    content = "I'm sorry, but I couldn't generate a meaningful response."
                    logger.warning("No content extracted from response")
                    
                # Log what we got
                logger.info(f"Extracted content (first 100 chars): {content[:100]}...")
                
                return content
                
            except Exception as e:
                logger.error(f"Error extracting content from response: {str(e)}")
                return "I'm sorry, but there was an error processing the response."
    
    # Override the get_llm_api function
    def get_llm_api():
        return DockerLLMAPI()
    
    # For compatibility, also provide a get_llm_engine function
    def get_llm_engine():
        return get_llm_api()
    
    logger.info("Successfully initialized Docker LLM API client")

except Exception as e:
    logger.error(f"Error initializing Docker LLM API client: {str(e)}")
    # Keep the fallback functions defined above

class ConversationManager:
    """
    Orchestrates conversation flow, interacting with memory, LLM, and components.
    Uses pre-initialized, user-scoped managers.
    Manages the currently active chat session for a user.
    
    Refactored to use modular components for better maintainability.
    """
    
    def __init__(self, 
                 user_id: str,
                 context_builder: Optional[ContextBuilder] = None,
                 file_manager: Optional[ChatFileManager] = None,
                 contextual_memory: Optional[ContextualMemoryManager] = None,
                 episodic_memory: Optional[EpisodicMemoryManager] = None):
        """
        Initialize conversation manager with pre-initialized, user-scoped managers
        and instantiate helper components. Does not load a session initially.
        
        Args:
            user_id: The ID of the user this manager instance belongs to.
            context_builder: Pre-initialized context builder for this user
            file_manager: Pre-initialized file manager for this user
            contextual_memory: Pre-initialized contextual memory manager for this user
            episodic_memory: Pre-initialized episodic memory manager for this user
        """
        self.logger = logging.getLogger(__name__)
        self.user_id = user_id
        self.current_session_id = None
        
        # Store the managers
        self.file_manager = file_manager
        self.contextual_memory = contextual_memory
        self.episodic_memory = episodic_memory
        
        # Initialize LLM API
        self.llm_api = get_llm_api()
        
        # Initialize the prompt builder
        self.prompt_builder = PromptBuilder(
            contextual_memory_manager=self.contextual_memory,
            episodic_memory_manager=self.episodic_memory
        )
        
        # Initialize the action handler for processing special commands
        self.action_handler = ActionHandler(
            contextual_memory_manager=self.contextual_memory,
            episodic_memory_manager=self.episodic_memory
        )
        
        # Initialize memory importance scorer
        self.memory_importance_scorer = MemoryImportanceScorer()
        
        # Initialize our refactored components
        self.search_handler = SearchHandler(
            logger=self.logger,
            contextual_memory=self.contextual_memory
        )
        
        # Get the memory system's context builder if we have access to it
        memory_context_builder = None
        if self.contextual_memory and hasattr(self.contextual_memory, 'context_builder'):
            memory_context_builder = self.contextual_memory.context_builder
            self.logger.info("Using contextual memory's existing context builder")
        
        self.context_builder = context_builder or ContextBuilder(
            logger=self.logger,
            context_builder=memory_context_builder,  # Use the memory system's context builder
            memory_manager=self.contextual_memory
        )
        
        self.response_processor = ResponseProcessor(
            logger=self.logger,
            llm_api=self.llm_api,
            action_handler=self.action_handler,
            contextual_memory=self.contextual_memory
        )
        
        # Keep track of memory pruning
        from managers.memory.memory_pruner import MemoryPruner
        
        # We'll need a database session for the memory pruner
        with get_db() as db_session:
            self.memory_pruner = MemoryPruner(
                db_session=db_session,
                episodic_memory_manager=self.episodic_memory,
                token_limit=30000
            )
        
        self.logger.info(f"ConversationManager initialized for user {user_id}")
    
    def load_session(self, session_id: str):
        """
        Load an existing session.
        
        Args:
            session_id: The session ID to load
        """
        self.current_session_id = session_id
        self.logger.info(f"Loaded session {session_id}")
    
    def get_response(self, db: SQLAlchemySession, user_input: str, session_id: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Process a user message and yield response chunks.
        This method is called by the API server.
        
        Args:
            db: SQLAlchemy database session
            user_input: The user's message
            session_id: Optional session ID to use. If not provided, the current session ID will be used
            
        Yields:
            Response chunks as dictionaries
        """
        if session_id:
            self.load_session(session_id)
        
        # Make sure we have a valid session
        if not self.current_session_id:
            error_response = {
                'type': 'error',
                'content': "No active session. Please create a new chat or select an existing one.",
                'timestamp': datetime.now().isoformat()
            }
            self.logger.error("No active session in get_response")
            yield error_response
            return
        
        # Process the message with our tiered memory system
        yield from self.process_tiered_message(user_input)
    
    def process_tiered_message(self, user_input: str) -> Generator[Dict[str, Any], None, None]:
        """
        Process a user message using the tiered memory system for optimal token efficiency.
        This implementation maintains coherence across long conversations while minimizing token usage.
        
        Args:
            user_input: The user's message
            
        Yields:
            Response chunks from the conversation
        """
        # Ensure we have a valid session
        if not self.current_session_id:
            self.logger.error("No active session. Cannot process message.")
            yield {
                'type': 'error',
                'content': "No active session.",
                'timestamp': datetime.now().isoformat()
            }
            return
        
        # Store the user message in the database with tiered representations
        user_message_id = self._store_user_message(user_input)
        
        # ENHANCEMENT: Check for direct web search request in user input
        # Delegate to the search handler component
        search_results = list(self.search_handler.process_search_request(user_input, self.current_session_id))
        for result in search_results:
            yield result
        
        # Check if memory pruning is needed
        self.memory_pruner.check_and_prune(self.current_session_id, self.user_id)
        
        # Build context with tiered history
        context = self.context_builder.build_tiered_context(
            session_id=self.current_session_id,
            user_input=user_input
        )
        
        # Prepare the system prompt using the correct method name (construct_prompt instead of build_system_prompt)
        system_prompt = self.prompt_builder.construct_prompt(
            session_id=self.current_session_id,
            user_input=user_input,
            web_search_results=search_results[0]['content'] if search_results else None
        )
        
        # Generate and process the response
        yield from self.response_processor.generate_response(
            user_input=user_input,
            system_prompt=system_prompt,
            context=context,
            session_id=self.current_session_id,
            user_id=self.user_id
        )
        
        # After conversation, check if any messages should be elevated in importance
        try:
            if self.contextual_memory:
                self.auto_upgrade_important_messages(self.current_session_id)
        except Exception as e:
            self.logger.error(f"Error in auto-upgrading messages: {str(e)}")
    
    def process_message(self, user_input: str, session_id: Optional[str] = None):
        """
        Process a user message and yield response chunks.
        This is an alias for process_tiered_message to maintain compatibility.
        
        Args:
            user_input: The user's message
            session_id: Optional session ID to use
            
        Yields:
            Response chunks from the conversation
        """
        # Set the session if provided
        if session_id and session_id != self.current_session_id:
            self.load_session(session_id)
            
        # Process the message using our tiered implementation
        for chunk in self.process_tiered_message(user_input):
            yield chunk
    
    def _store_user_message(self, user_input: str) -> Optional[str]:
        """
        Store a user message in the database with tiered representations.
        
        Args:
            user_input: The user's message text
            
        Returns:
            ID of the stored message, or None if storage failed
        """
        if not self.contextual_memory:
            self.logger.warning("No contextual memory manager available, cannot store user message")
            return None
            
        try:
            # Instead of using add_user_message, use process_user_message
            message_id = self._generate_message_id()
            
            # Process the user message
            self.contextual_memory.process_user_message(self.current_session_id, user_input)
            
            # Note: This method doesn't return a message ID, so we generate our own
            self.logger.info(f"Processed user message in contextual memory with ID {message_id}")
            
            # Extract and store facts from the user message
            # This functionality is built into the ContextualMemoryManager
            # so we don't need to call extract_and_store_facts separately
            
            return message_id
            
        except Exception as e:
            self.logger.error(f"Error storing user message: {str(e)}")
            return None
            
    def _generate_message_id(self):
        """Generate a unique message ID"""
        return str(uuid.uuid4())
    
    def auto_upgrade_important_messages(self, session_id: str, message_limit: int = 10) -> int:
        """
        Automatically upgrade important messages based on their content.
        This uses the memory importance scorer to identify which messages should be in higher tiers.
        
        Args:
            session_id: The session ID
            message_limit: Maximum number of recent messages to analyze
            
        Returns:
            Number of messages upgraded
        """
        if not self.contextual_memory or not self.memory_importance_scorer:
            return 0
            
        try:
            # Get recent messages from Tier 3 (low importance)
            tier3_messages = self.contextual_memory.get_tier_messages(
                session_id=session_id,
                tier=3,
                limit=message_limit,
                include_system=False
            )
            
            # Skip if no messages to analyze
            if not tier3_messages:
                return 0
                
            # Score the messages
            scored_messages = self.memory_importance_scorer.score_messages(
                messages=tier3_messages,
                session_id=session_id
            )
            
            # Upgrade messages with high importance scores
            upgrade_count = 0
            for message_id, score in scored_messages.items():
                if score >= 0.7:  # High importance threshold
                    # Upgrade to Tier 1 (high importance)
                    self.contextual_memory.upgrade_message_tier(
                        message_id=message_id,
                        new_tier=1
                    )
                    self.logger.info(f"Auto-upgraded message {message_id} to Tier 1 with score {score}")
                    upgrade_count += 1
                elif score >= 0.4:  # Medium importance threshold
                    # Upgrade to Tier 2 (medium importance)
                    self.contextual_memory.upgrade_message_tier(
                        message_id=message_id,
                        new_tier=2
                    )
                    self.logger.info(f"Auto-upgraded message {message_id} to Tier 2 with score {score}")
                    upgrade_count += 1
                    
            return upgrade_count
                
        except Exception as e:
            self.logger.error(f"Error in auto_upgrade_important_messages: {str(e)}")
            return 0
