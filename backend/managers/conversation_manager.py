# RAI_Chat/Backend/managers/conversation_manager.py
# Standard conversation manager for the RAI Chat application

import json
import os
import re
import requests
import logging
import importlib.util
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Generator, Tuple, Union
from sqlalchemy.orm import Session as SQLAlchemySession

# Import database connection
from core.database.connection import get_db

# Import other managers and components
from managers.memory.contextual_memory import ContextualMemoryManager
from managers.memory.episodic_memory import EpisodicMemoryManager
from managers.chat_file_manager import ChatFileManager
from components.prompt_builder import PromptBuilder
from components.action_handler import ActionHandler
from utils.path import ensure_directory_exists_str

# Set up logging
logger = logging.getLogger(__name__)

# Define constants
LOGS_DIR = os.path.join('/app', 'data', 'logs')
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
            self.llm_api_url = os.environ.get('LLM_API_URL', 'http://llm-engine:6101')
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
                    return response.json()
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
            try:
                response = self.generate_response(prompt)
                
                # Return in the expected format for memory extraction
                if isinstance(response, dict) and "response" in response:
                    return {"text": response["response"]}
                elif isinstance(response, str):
                    return {"text": response}
                else:
                    return {"text": str(response)}
            except Exception as e:
                logger.error(f"Error in generate_text: {str(e)}")
                return {"text": f"Error: {str(e)}"}
        
        def chat_completion(self, messages, temperature=0.7, max_tokens=1000, session_id=None):
            """Process a chat completion request - for memory extraction.
            For compatibility with the expected format in contextual_memory.py
            """
            try:
                # Extract messages
                system_msg = ""
                user_msg = ""
                
                for msg in messages:
                    if msg["role"] == "system":
                        system_msg = msg["content"]
                    elif msg["role"] == "user":
                        user_msg = msg["content"]
                
                # Call the generate_response method
                response = self.generate_response(user_msg, system_msg)
                
                # Format the response as expected by the memory manager
                if isinstance(response, dict) and "response" in response:
                    content = response["response"]
                elif isinstance(response, str):
                    content = response
                else:
                    content = str(response)
                
                # First try returning the format expected by the code from the working version
                # This format works with our updated contextual_memory.py
                return {"content": content}
            except Exception as e:
                logger.error(f"Error in chat_completion: {str(e)}")
                return {"content": f"Error: {str(e)}"}
    
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
    """
    
    def __init__(self, 
                 user_id: str,  # For Docker, we use string user IDs
                 session_id: Optional[str] = None,
                 file_manager: Optional[ChatFileManager] = None,
                 contextual_memory: Optional[ContextualMemoryManager] = None,
                 episodic_memory: Optional[EpisodicMemoryManager] = None):
        """
        Initialize conversation manager with pre-initialized, user-scoped managers
        and instantiate helper components. Does not load a session initially.
        
        Args:
            user_id: The ID of the user this manager instance belongs to.
            session_id: Optional session ID to load initially.
            file_manager: An initialized ChatFileManager instance.
            contextual_memory: An initialized ContextualMemoryManager instance.
            episodic_memory: An initialized EpisodicMemoryManager instance.
        """
        self.user_id = user_id
        self.logger = logging.getLogger(f"ConvMgr_User{self.user_id}")
        
        # --- Logging Setup ---
        if not self.logger.hasHandlers():
            log_dir_path = LOGS_DIR
            try:
                os.makedirs(log_dir_path, exist_ok=True)
                log_file_path = os.path.join(log_dir_path, f'conversation_user_{self.user_id}.log')
                handler = logging.FileHandler(log_file_path, encoding='utf-8')
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
            except Exception as e:
                logger.error(f"CRITICAL: Failed to set up file logging for ConvMgr user {self.user_id}: {e}", exc_info=True)
        # --- End Logging Setup ---
        
        # Assign or create managers
        # Initialize managers in correct order with proper parameters
        # First, create the file manager
        self.chat_file_manager = file_manager or ChatFileManager()
        
        # Next, create the episodic memory manager (takes only user_id)
        self.episodic_memory = episodic_memory or EpisodicMemoryManager(
            user_id=user_id
        )
        
        # Then, create the contextual memory manager (needs user_id and episodic memory manager)
        self.contextual_memory = contextual_memory or ContextualMemoryManager(
            user_id=user_id,
            episodic_memory_manager=self.episodic_memory
        )
        
        # Store the session_id for later use
        self.current_session_id = session_id or self.chat_file_manager.create_new_session_id()
        
        # Instantiate helper components
        self.prompt_builder = PromptBuilder(self.contextual_memory, self.episodic_memory)
        self.action_handler = ActionHandler(self.contextual_memory, self.episodic_memory)
        
        self.logger.info(f"ConversationManager initialized for User ID: {self.user_id}, Session ID: {self.current_session_id}")
        
        # Track last message times
        self.last_user_message = None
        self.last_response_time = None
        self.last_assistant_message = None
        
        # Initialize LLM API access
        self.llm_api = get_llm_api()
        self.llm_engine = get_llm_engine()
    
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
        # Simply delegate to process_message
        yield from self.process_message(user_input, session_id)
    
    def process_message(self, user_input: str, session_id: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Process a user message and yield response chunks.
        
        Args:
            user_input: The user's message.
            session_id: Optional session ID to use. If not provided, the current session ID will be used.
            
        Yields:
            Response chunks as dictionaries.
        """
        # Set the session ID if provided
        if session_id and session_id != self.current_session_id:
            # Just update our local session_id
            self.current_session_id = session_id
            # Memory managers no longer track session_id directly
        
        # Load user's remembered facts from the database before processing
        try:
            # Use proper database context manager
            with get_db() as db:
                # Load remembered facts from database
                self.contextual_memory.load_user_remembered_facts(db)
                self.logger.info(f"Loaded remembered facts from database for user {self.user_id}")
        except Exception as e:
            self.logger.error(f"Error loading remembered facts: {e}")
            
        # We'll rely on the LLM-based extraction in contextual_memory.process_assistant_message
        # instead of hardcoding pattern matching
        
        # Record the user message
        self.last_user_message = {
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # ENHANCEMENT: Check for direct web search request in user input
        if '[SEARCH:' in user_input:
            import re
            direct_search_match = re.search(r"\[SEARCH:\s*(.+?)\s*\]", user_input)
            if direct_search_match:
                query = direct_search_match.group(1).strip()
                self.logger.info(f"Direct web search requested for: {query}")
                
                # Create a system message indicating search is happening
                yield {
                    'type': 'system',
                    'action': 'web_search',
                    'status': 'active',
                    'content': f"Searching the web for: {query}",
                    'timestamp': datetime.now().isoformat(),
                    'session_id': self.current_session_id
                }
                
                # Attempt to perform the search
                try:
                    from components.action_handler import perform_search
                    search_results = perform_search(query=query)
                    
                    # Send the results directly
                    yield {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'complete',
                        'content': search_results,
                        'timestamp': datetime.now().isoformat(),
                        'session_id': self.current_session_id
                    }
                    
                    # Continue with normal processing
                    self.logger.info("Web search completed, continuing with LLM processing")
                except Exception as e:
                    self.logger.error(f"Error performing direct web search: {e}")
                    yield {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'error',
                        'content': f"Error performing web search: {str(e)}",
                        'timestamp': datetime.now().isoformat(),
                        'session_id': self.current_session_id
                    }
        
        # Build the system prompt
        system_prompt = self.prompt_builder.construct_prompt(
            session_id=self.current_session_id,
            user_input=user_input
        )
        
        # Generate the LLM response
        try:
            # Get the response from the LLM API
            response_data = self.llm_api.generate_response(user_input, system_prompt)
            
            # Extract the response text
            if isinstance(response_data, dict):
                if 'response' in response_data:
                    # Direct response field
                    response_text = response_data['response']
                elif 'text' in response_data:
                    # Some API responses use 'text' field
                    response_text = response_data['text']
                elif 'choices' in response_data and len(response_data['choices']) > 0:
                    # OpenAI-style response format
                    choice = response_data['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        response_text = choice['message']['content']
                    elif 'text' in choice:
                        response_text = choice['text']
                    else:
                        response_text = str(choice)
                else:
                    # Fallback - convert the entire response to a string
                    response_text = str(response_data)
            else:
                # Not a dictionary
                response_text = str(response_data)
                
            # Ensure it's not a stringified dictionary from the LLM API
            if response_text.startswith("{'status'") and "'text'" in response_text:
                try:
                    # Try to parse it as a dict-like string
                    import ast
                    parsed = ast.literal_eval(response_text)
                    if isinstance(parsed, dict) and 'text' in parsed:
                        response_text = parsed['text']
                except Exception as parse_err:
                    self.logger.warning(f"Failed to parse response_text as dict: {parse_err}")
            
            # Format the response in the structure expected by ActionHandler
            formatted_response = {
                'llm_response': {
                    'content': response_text,  # Add content directly
                },
                'tier3_response': response_text  # Add tier3_response at the top level as expected by ActionHandler
            }
            
            # Store the assistant response in contextual memory with session_id
            self.contextual_memory.process_assistant_message(response_data, user_input, session_id=self.current_session_id)
            
            # Process the response through the action handler
            action_signal, action_result, action_type = None, None, None
            try:
                # Collect all response chunks and/or final signal
                for result in self.action_handler.process_llm_response(
                    self.current_session_id, user_input, formatted_response
                ):
                    if isinstance(result, tuple) and len(result) == 3:
                        # This is the final signal from action handler
                        action_signal, action_result, action_type = result
                        break
                    else:
                        # This is a response chunk (e.g. status update)
                        response_chunk = result
                        # Add the session ID to the response chunk
                        response_chunk['session_id'] = self.current_session_id
                        # Yield the response chunk
                        yield response_chunk
            except Exception as e:
                self.logger.error(f"Error processing action handler response: {e}", exc_info=True)
                # On error, extract the tier3 content directly from the LLM response and use it
                try:
                    tier3_response = formatted_response.get('tier3_response', '')
                    if tier3_response:
                        self.logger.info(f"Using tier3 response directly due to action handler error")
                        action_signal = 'break'
                        action_result = tier3_response
                        action_type = 'answer'
                    else:
                        # Fallback to the original LLM response
                        original_response = formatted_response.get('llm_response', {}).get('content', '')
                        self.logger.info(f"Using original response due to action handler error")
                        action_signal = 'break'
                        action_result = original_response or f"Error processing chat response: {str(e)}"
                        action_type = 'answer'
                except Exception as extract_error:
                    self.logger.error(f"Error extracting tier3 content: {extract_error}", exc_info=True)
                    yield {
                        'type': 'error',
                        'content': f"Error processing chat response: {str(e)}",
                        'session_id': self.current_session_id
                    }
                    return
            
            # If we got a final result from action handler
            if action_signal and action_type == 'answer':
                # Format the result as expected by frontend - only send the necessary fields
                # Remove the full llm_response structure to simplify what's sent to the frontend
                final_response = {
                    'type': 'final',
                    'content': action_result,
                    'session_id': self.current_session_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Record the assistant message
                self.last_assistant_message = {
                    'role': 'assistant',
                    'content': action_result,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.last_response_time = time.time()
                
                # Yield the final response
                yield final_response
                
                # Save the session transcript and metadata to the database
                try:
                    # Structure the transcript data from the conversation history
                    transcript_data = []
                    
                    # Add user message
                    if self.last_user_message:
                        transcript_data.append(self.last_user_message)
                    
                    # Add assistant message
                    if self.last_assistant_message:
                        transcript_data.append(self.last_assistant_message)
                    
                    # Create session metadata
                    session_metadata = {
                        'title': user_input[:50] if len(user_input) > 50 else user_input  # Use first 50 chars of user message as title
                    }
                    
                    # Save the session to the database
                    with get_db() as db:
                        # Save the session transcript and metadata
                        success = self.chat_file_manager.save_session_transcript(
                            db, 
                            int(self.user_id), 
                            self.current_session_id, 
                            transcript_data, 
                            session_metadata
                        )
                        
                        if success:
                            self.logger.info(f"Saved session {self.current_session_id} to database for user {self.user_id}")
                        else:
                            self.logger.error(f"Failed to save session {self.current_session_id} to database")
                        
                        # Save any newly extracted memories back to the database
                        self.contextual_memory.save_user_remembered_facts(db)
                except Exception as e:
                    self.logger.error(f"Error saving session or memories to database: {e}", exc_info=True)
        
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}", exc_info=True)
            yield {
                'type': 'error',
                'content': f"Error processing message: {str(e)}",
                'session_id': self.current_session_id
            }
    
    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self.current_session_id
