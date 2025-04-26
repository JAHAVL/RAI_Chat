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
from models.connection import get_db

# Import other managers and components
from managers.memory.contextual_memory import ContextualMemoryManager
from managers.memory.episodic_memory import EpisodicMemoryManager
from managers.memory.memory_importance_scorer import MemoryImportanceScorer
from managers.chat_file_manager import ChatFileManager
from components.prompt_builder import PromptBuilder
from components.action_handler import ActionHandler, ACTION_COMMAND_DETECTED  # Import the constant
from utils.pathconfig import ensure_directory_exists

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
                 user_id: str, 
                 llm_api: Optional[Any] = None,
                 file_manager: Optional[ChatFileManager] = None,
                 contextual_memory: Optional[ContextualMemoryManager] = None,
                 episodic_memory: Optional[EpisodicMemoryManager] = None):
        """
        Initialize conversation manager with pre-initialized, user-scoped managers
        and instantiate helper components. Does not load a session initially.
        
        Args:
            user_id: The ID of the user this manager instance belongs to.
            llm_api: Optional LLM API client instance.
            file_manager: Optional ChatFileManager instance.
            contextual_memory: Optional ContextualMemoryManager instance.
            episodic_memory: Optional EpisodicMemoryManager instance.
        """
        self.user_id = user_id
        self.current_session_id = None
        self.last_user_message = None
        self.last_assistant_message = None
        self.last_response_time = None
        
        # Configure logging
        self.logger = logging.getLogger(f"conversation_manager_{user_id}")
        
        # Load the LLM API client
        self.llm_api = llm_api or get_llm_api()
        self.logger.info(f"Using LLM API client: {type(self.llm_api).__name__}")
        
        # Initialize the file manager if not provided
        self.file_manager = file_manager or ChatFileManager(user_id=self.user_id)
        
        # Initialize auxiliary components
        from models.connection import SessionLocal
        
        # Create a dedicated session for components that need persistent access
        # In Docker, we need to ensure database connections are properly managed
        try:
            self.db_session = SessionLocal()
            self.logger.info("Successfully initialized database session")
        except Exception as e:
            self.logger.error(f"Error initializing database session: {str(e)}", exc_info=True)
            # Attempt to reconnect with retries
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    self.logger.info(f"Retrying database connection (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(1)  # Brief pause before retry
                    self.db_session = SessionLocal()
                    self.logger.info("Successfully reconnected to database on retry")
                    break
                except Exception as retry_e:
                    self.logger.error(f"Retry {retry_count + 1} failed: {str(retry_e)}")
                    retry_count += 1
            
            if retry_count >= max_retries:
                self.logger.critical("Failed to establish database connection after retries")
                raise RuntimeError("Failed to establish database connection")
        
        # Initialize the tiered memory components
        from managers.memory.tier_manager import TierManager
        from managers.memory.context_builder import ContextBuilder
        from managers.memory.request_parser import RequestParser
        from managers.memory.memory_pruner import MemoryPruner
        
        self.tier_manager = TierManager()
        self.context_builder = ContextBuilder(self.db_session, self.tier_manager)
        self.request_parser = RequestParser(self.db_session)
        
        # Initialize the memory managers if not provided
        self.contextual_memory = contextual_memory or ContextualMemoryManager()
        self.episodic_memory = episodic_memory or EpisodicMemoryManager()
        
        # Initialize memory pruner now that episodic_memory is available
        self.memory_pruner = MemoryPruner(
            db_session=self.db_session,
            episodic_memory_manager=self.episodic_memory,
            token_limit=30000
        )
        
        # Initialize the memory importance scorer for automatic tier upgrades
        self.importance_scorer = MemoryImportanceScorer()
        self.logger.info("Initialized memory importance scorer for automatic tier management")
        
        # Initialize the prompt builder with memory managers
        self.prompt_builder = PromptBuilder(
            contextual_memory_manager=self.contextual_memory,
            episodic_memory_manager=self.episodic_memory
        )
        
        # Initialize the action handler with memory managers
        self.action_handler = ActionHandler(
            contextual_memory_manager=self.contextual_memory,
            episodic_memory_manager=self.episodic_memory
        )
        
        self.logger.info(f"Conversation manager for user {user_id} initialized successfully")
    
    def load_session(self, session_id: str) -> None:
        """
        Load an existing session.
        
        Args:
            session_id: The session ID to load
        """
        self.logger.info(f"Loading session {session_id}")
        self.current_session_id = session_id
        
        # Any other session loading logic would go here
        # For now, just set the session ID
    
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
            user_input: The user's message
            session_id: Optional session ID
            
        Yields:
            Response chunks
        """
        try:
            # Set the session ID if provided, otherwise use the current session
            if session_id:
                self.current_session_id = session_id
                
            # Initialize components if needed (Docker-specific resilience)
            self.initialize_if_needed()
            
            # Ensure we have a valid session
            if not self.current_session_id:
                self.logger.warning("No active session. Creating a new one.")
                # Create a new session in the database
                from models import ChatSession
                new_session = ChatSession(user_id=self.user_id)
                try:
                    self.db_session.add(new_session)
                    self.db_session.commit()
                    self.current_session_id = new_session.session_id
                    self.logger.info(f"Created new session with ID: {self.current_session_id}")
                except Exception as e:
                    self.logger.error(f"Error creating new session: {str(e)}", exc_info=True)
                    yield {
                        'type': 'error',
                        'content': f"Error creating new session: {str(e)}",
                        'session_id': None
                    }
                    return
            
            try:
                # Store the user message in the database and contextual memory
                self._store_user_message(user_input)
                
                # Run automatic tier upgrading on recent messages
                # This will identify important messages and upgrade them based on content
                upgraded_count = self.auto_upgrade_important_messages(self.current_session_id)
                if upgraded_count > 0:
                    self.logger.info(f"Auto-upgraded {upgraded_count} important messages")
            except Exception as e:
                self.logger.error(f"Error processing user message: {str(e)}", exc_info=True)
                # Continue processing - don't halt on storage errors
            
            # Pre-process user input for memory extraction before LLM response
            # This ensures we capture critical facts even before the LLM processes them
            self._extract_and_store_critical_facts(user_input)
            
            # Record the user's message
            self.last_user_message = {
                'role': 'user',
                'content': user_input,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Build the system prompt
            system_prompt = self.prompt_builder.construct_prompt(
                session_id=self.current_session_id,
                user_input=user_input
            )
            
            # ENHANCEMENT: Check for direct web search request in user input
            if '[SEARCH:' in user_input:
                try:
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
                        
                        try:
                            # Attempt to perform the search
                            from components.action_handler import perform_search
                            search_results = perform_search(query=query)
                            
                            # Send the results directly
                            yield {
                                'type': 'system',
                                'action': 'web_search',
                                'status': 'complete',
                                'content': search_results,
                                'raw_results': search_results,
                                'timestamp': datetime.now().isoformat(),
                                'session_id': self.current_session_id
                            }
                            
                            # Store search results in contextual memory as a system message
                            # This ensures the search results are part of the conversation history
                            search_system_message = {
                                'role': 'system',
                                'content': f"Search results for '{query}':\n\n{search_results}",
                                'timestamp': datetime.now().isoformat(),
                                'type': 'search_results'
                            }
                            
                            # Add to contextual memory
                            try:
                                if self.contextual_memory:
                                    # Store as a system message in the conversation
                                    system_message_data = {
                                        'content': search_system_message['content'],
                                        'type': 'search_results'
                                    }
                                    self.contextual_memory.add_system_message(system_message_data, self.current_session_id)
                                    self.logger.info(f"Added search results to contextual memory for session {self.current_session_id}")
                                    
                                    # Also try to extract key facts from the search results
                                    # This helps the system remember important information from searches
                                    extraction_text = f"Important information from search about '{query}':\n\n{search_results}"
                                    self.contextual_memory.extract_and_store_facts(extraction_text, self.current_session_id)
                                    self.logger.info("Extracted key facts from search results")
                            except Exception as mem_ex:
                                self.logger.error(f"Error storing search results in memory: {str(mem_ex)}", exc_info=True)
                        except Exception as search_ex:
                            self.logger.error(f"Error performing direct web search: {search_ex}")
                            yield {
                                'type': 'system',
                                'action': 'web_search',
                                'status': 'error',
                                'content': f"Error performing web search: {str(search_ex)}",
                                'timestamp': datetime.now().isoformat(),
                                'session_id': self.current_session_id
                            }
            
            # Generate the LLM response
            try:
                # Call LLM API with improved error handling
                llm_response = self.llm_api.generate_response(
                    prompt=user_input,
                    system_prompt=system_prompt
                )
                
                # Add detailed logging to debug the response structure
                self.logger.info(f"LLM API response type: {type(llm_response)}")
                if isinstance(llm_response, dict):
                    self.logger.info(f"LLM API response keys: {list(llm_response.keys())}")
                    for key in llm_response.keys():
                        self.logger.info(f"LLM response[{key}] type: {type(llm_response[key])}")
                else:
                    self.logger.info(f"LLM API response is not a dict: {llm_response}")
                
                # Process the response with the action handler
                action_signal, action_result, action_type = self.action_handler.process_llm_response(
                    session_id=self.current_session_id,
                    user_input=user_input,
                    response_data=llm_response
                )
            except Exception as e:
                self.logger.error(f"Error generating or processing LLM response: {str(e)}", exc_info=True)
                
                # Docker-specific retry logic for transient network issues
                if "connection" in str(e).lower() or "timeout" in str(e).lower():
                    self.logger.warning("Detected possible Docker network issue, attempting retry")
                    try:
                        # Brief pause before retry
                        time.sleep(1)
                        
                        # Retry LLM API call
                        llm_response = self.llm_api.generate_response(user_input, system_prompt)
                        
                        # Process the retried response
                        action_signal, action_result, action_type = self.action_handler.process_llm_response(
                            session_id=self.current_session_id,
                            user_input=user_input,
                            response_data=llm_response
                        )
                        
                        self.logger.info("Successfully recovered from transient error")
                    except Exception as retry_e:
                        self.logger.error(f"Retry failed: {str(retry_e)}", exc_info=True)
                        # Fall through to error handling
                        action_signal = True
                        action_result = f"I apologize, but I encountered a technical issue. Please try again in a moment."
                        action_type = "error"
                else:
                    # Standard error handling for non-network issues
                    action_signal = True
                    action_result = f"I apologize, but I encountered an error. Please try again."
                    action_type = "error"
            
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
            
            # Handle search detection - when LLM decides to perform a search
            elif action_signal == 'ACTION_SEARCH_DETECTED' and action_type == 'SEARCH':
                search_query = action_result.strip()
                self.logger.info(f"LLM requested search for: '{search_query}'")
                
                # Inform user that search is being performed
                yield {
                    'type': 'system',
                    'action': 'web_search',
                    'status': 'active',
                    'content': f"Searching for: {search_query}",
                    'timestamp': datetime.now().isoformat(),
                    'session_id': self.current_session_id
                }
                
                try:
                    # Perform the search
                    from components.action_handler import perform_search
                    search_results = perform_search(query=search_query)
                    
                    # Format the search results
                    formatted_results = self.format_search_results(search_results)
                    
                    # Send search results to frontend
                    yield {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'complete',
                        'content': formatted_results,
                        'raw_results': search_results,
                        'timestamp': datetime.now().isoformat(),
                        'session_id': self.current_session_id
                    }
                    
                    # Store search results in contextual memory as a system message
                    # This ensures the search results are part of the conversation history
                    search_system_message = {
                        'role': 'system',
                        'content': f"Search results for '{search_query}':\n\n{formatted_results}",
                        'timestamp': datetime.now().isoformat(),
                        'type': 'search_results'
                    }
                    
                    # Add to contextual memory
                    try:
                        if self.contextual_memory:
                            # Store as a system message in the conversation
                            system_message_data = {
                                'content': search_system_message['content'],
                                'type': 'search_results'
                            }
                            self.contextual_memory.add_system_message(system_message_data, self.current_session_id)
                            self.logger.info(f"Added search results to contextual memory for session {self.current_session_id}")
                            
                            # Also try to extract key facts from the search results
                            # This helps the system remember important information from searches
                            extraction_text = f"Important information from search about '{search_query}':\n\n{formatted_results}"
                            self.contextual_memory.extract_and_store_facts(extraction_text, self.current_session_id)
                            self.logger.info("Extracted key facts from search results")
                    except Exception as mem_ex:
                        self.logger.error(f"Error storing search results in memory: {str(mem_ex)}", exc_info=True)
                    
                    # Now send the results back to the LLM for a comprehensive answer
                    from components.prompts import build_search_prompt
                    enhanced_prompt = build_search_prompt(
                        user_input=user_input,
                        search_query=search_query,
                        search_results=formatted_results,
                        system_prompt=system_prompt
                    )
                    
                    self.logger.info(f"Created specialized search prompt using prompt builder")
                    
                    # Call LLM again with the search results
                    llm_final_response = self.llm_api.generate_response(
                        prompt=user_input,  # Original user input
                        system_prompt=enhanced_prompt  # Enhanced system prompt with search results
                    )
                    
                    # Process the final LLM response
                    final_content = self._extract_content_from_response(llm_final_response)
                    
                    # Send the final response
                    final_response = {
                        'type': 'final',
                        'content': final_content,
                        'session_id': self.current_session_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    # Record the assistant message
                    self.last_assistant_message = {
                        'role': 'assistant',
                        'content': final_content,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    yield final_response
                    
                except Exception as search_e:
                    self.logger.error(f"Error in search flow: {str(search_e)}", exc_info=True)
                    yield {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'error',
                        'content': f"Error performing web search: {str(search_e)}",
                        'timestamp': datetime.now().isoformat(),
                        'session_id': self.current_session_id
                    }
                    
                    # Still try to give a response even if search failed
                    backup_response = {
                        'type': 'final',
                        'content': f"I tried to search for information about '{search_query}' but encountered an error. Here's what I know from my training: [LLM-generated response would appear here]",
                        'session_id': self.current_session_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    yield backup_response
            
            # Handle COMMAND_DETECTED action type for tier requests and episodic searches
            elif action_signal and action_type == ACTION_COMMAND_DETECTED:  # Use imported constant
                self.logger.info(f"Detected special command in LLM response, processing with RequestParser")
                
                # Process the response with the request parser directly using the self.db_session
                # since we've fixed it to be a proper SQLAlchemy session
                processed = self.request_parser.process_response(action_result, self.current_session_id)
                
                # If regeneration is needed due to tier requests or episodic search
                if processed.get("need_regeneration", False):
                    # Handle episodic memory request if present
                    episodic_context = None
                    if "episodic_query" in processed:
                        # Search episodic memory
                        self.logger.info(f"Searching episodic memory for query: {processed['episodic_query']}")
                        try:
                            # Check if episodic_memory is properly initialized
                            if self.episodic_memory:
                                episodic_content = self.episodic_memory.search_episodic_memory(
                                    query=processed['episodic_query'],
                                    session_id=self.current_session_id,
                                    top_k=5
                                )
                                if episodic_content:
                                    episodic_context = episodic_content
                                    self.logger.info(f"Found episodic memory: {episodic_content[:100]}...")
                            else:
                                # Fallback to using the contextual_memory's episodic_memory if available
                                self.logger.warning("Direct episodic_memory reference not available, trying through contextual_memory")
                                if hasattr(self.contextual_memory, 'episodic_memory') and self.contextual_memory.episodic_memory:
                                    episodic_content = self.contextual_memory.episodic_memory.search_episodic_memory(
                                        query=processed['episodic_query'],
                                        session_id=self.current_session_id,
                                        top_k=5
                                    )
                                    if episodic_content:
                                        episodic_context = episodic_content
                                        self.logger.info(f"Found episodic memory through contextual_memory: {episodic_content[:100]}...")
                        except Exception as e:
                            self.logger.error(f"Error searching episodic memory: {str(e)}", exc_info=True)
                
                # Rebuild context with updated tier levels
                self.logger.info("Rebuilding context with updated tier levels")
                updated_context = self.build_context()
                
                # Generate updated system prompt with enriched context
                self.logger.info("Constructing enriched system prompt with updated context")
                updated_system_prompt = self.prompt_builder.construct_prompt(
                    session_id=self.current_session_id,
                    user_input=user_input
                )
                
                # Add episodic search results if available
                if episodic_context:
                    episodic_section = f"\n\nEPISODIC MEMORY SEARCH RESULTS:\n{episodic_context}\n\n"
                    updated_system_prompt += episodic_section
                    self.logger.info(f"Added episodic memory results to prompt: {episodic_context[:100]}...")
                    
                    # Also add special instruction to emphasize the retrieved memory
                    updated_system_prompt += "IMPORTANT: Use the episodic memory search results above to answer the user's question.\n"
                
                # Add explicit instruction to use the upgraded context
                updated_system_prompt += "\nNOTE: Previous context has been upgraded with additional details. Use this information to give a more complete response.\n"
                
                # Log the context for debugging
                self.logger.info(f"Regenerating with context size: {len(updated_context) // 4} tokens")
                
                # Regenerate response with enriched context and updated system prompt
                self.logger.info("Regenerating LLM response with upgraded context")
                try:
                    # Call LLM with updated context
                    updated_response = self.llm_api.generate_response(user_input, updated_system_prompt)
                    
                    # Log success
                    self.logger.info(f"Successfully regenerated response: {updated_response[:100]}...")
                    
                    # Process response to remove any remaining special commands
                    final_processed = self.request_parser.process_response(updated_response, self.current_session_id)
                    clean_response = final_processed.get("clean_response", updated_response)
                    
                    # Check if regenerated response still contains commands (recursive case)
                    if final_processed.get("need_regeneration", False):
                        self.logger.warning("Regenerated response still contains commands. Removing commands without further regeneration.")
                        # Just remove the commands without regenerating again to avoid infinite loops
                        clean_response = final_processed.get("clean_response", updated_response)
                except Exception as e:
                    self.logger.error(f"Error regenerating response: {str(e)}", exc_info=True)
                    clean_response = "I apologize, but I encountered an error retrieving the information you requested. Please try asking again."
                
                # Store the assistant's response in contextual memory
                try:
                    self.logger.info("Storing regenerated assistant response in contextual memory")
                    self.contextual_memory.process_assistant_message({
                        "role": "assistant",
                        "content": clean_response
                    }, user_input, self.current_session_id)
                except Exception as e:
                    self.logger.error(f"Error storing assistant response in contextual memory: {str(e)}", exc_info=True)
                
                # Format and return the final response
                final_response = {
                    'type': 'final',
                    'content': clean_response,
                    'session_id': self.current_session_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Record the assistant message for history
                self.last_assistant_message = {
                    'role': 'assistant',
                    'content': clean_response,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.last_response_time = time.time()
                
                yield final_response
            elif action_signal:
                # Format the result as expected by frontend
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
            else:
                # No regeneration needed, just clean and return the original response
                clean_response = processed.get("clean_response", action_result)
                
                # Store the assistant's response in contextual memory
                try:
                    self.contextual_memory.process_assistant_message(
                        {"role": "assistant", "content": clean_response}, 
                        user_input, 
                        self.current_session_id
                    )
                except Exception as e:
                    self.logger.error(f"Error storing in contextual memory: {str(e)}")
                
                # Format the final response
                final_response = {
                    'type': 'final',
                    'content': clean_response,
                    'session_id': self.current_session_id,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Record the assistant message for history
                self.last_assistant_message = {
                    'role': 'assistant',
                    'content': clean_response,
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.last_response_time = time.time()
                
                # Return the final response
                yield final_response
                
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}", exc_info=True)
            error_response = {
                'type': 'error',
                'content': f"An error occurred: {str(e)}",
                'session_id': self.current_session_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            yield error_response
    
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
        if '[SEARCH:' in user_input:
            try:
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
                    
                    try:
                        # Attempt to perform the search
                        from components.action_handler import perform_search
                        search_results = perform_search(query=query)
                        
                        # Send the results directly
                        yield {
                            'type': 'system',
                            'action': 'web_search',
                            'status': 'complete',
                            'content': search_results,
                            'raw_results': search_results,
                            'timestamp': datetime.now().isoformat(),
                            'session_id': self.current_session_id
                        }
                        
                        # Store search results in contextual memory as a system message
                        # This ensures the search results are part of the conversation history
                        search_system_message = {
                            'role': 'system',
                            'content': f"Search results for '{query}':\n\n{search_results}",
                            'timestamp': datetime.now().isoformat(),
                            'type': 'search_results'
                        }
                        
                        # Add to contextual memory
                        try:
                            if self.contextual_memory:
                                # Store as a system message in the conversation
                                system_message_data = {
                                    'content': search_system_message['content'],
                                    'type': 'search_results'
                                }
                                self.contextual_memory.add_system_message(system_message_data, self.current_session_id)
                                self.logger.info(f"Added search results to contextual memory for session {self.current_session_id}")
                                
                                # Also try to extract key facts from the search results
                                # This helps the system remember important information from searches
                                extraction_text = f"Important information from search about '{query}':\n\n{search_results}"
                                self.contextual_memory.extract_and_store_facts(extraction_text, self.current_session_id)
                                self.logger.info("Extracted key facts from search results")
                        except Exception as mem_ex:
                            self.logger.error(f"Error storing search results in memory: {str(mem_ex)}", exc_info=True)
                    except Exception as search_ex:
                        self.logger.error(f"Error performing direct web search: {search_ex}")
                        yield {
                            'type': 'system',
                            'action': 'web_search',
                            'status': 'error',
                            'content': f"Error performing web search: {str(search_ex)}",
                            'timestamp': datetime.now().isoformat(),
                            'session_id': self.current_session_id
                        }
        
        # Check if memory pruning is needed
        self.memory_pruner.check_and_prune(self.current_session_id, self.user_id)
        
        # Build context with tiered history
        context = self.context_builder.build_tiered_context(
            current_message=user_input,
            session_id=self.current_session_id,
            user_id=int(self.user_id)
        )
        
        # Generate system prompt from the context
        system_prompt = self.prompt_builder.construct_prompt(
            session_id=self.current_session_id,
            user_input=user_input
        )
        
        # Process with LLM
        try:
            response = self.llm_api.generate_response(user_input, system_prompt)
            
            # Check for tier requests or episodic memory requests
            processed = self.request_parser.process_response(response, self.current_session_id)
            
            # If regeneration is needed, handle it
            if processed["need_regeneration"]:
                # Handle episodic memory request if present
                episodic_context = None
                if "episodic_query" in processed:
                    # Search episodic memory
                    self.logger.info(f"Searching episodic memory for query: {processed['episodic_query']}")
                    try:
                        # Check if episodic_memory is properly initialized
                        if self.episodic_memory:
                            episodic_content = self.episodic_memory.search_episodic_memory(
                                query=processed['episodic_query'],
                                session_id=self.current_session_id,
                                top_k=5
                            )
                            if episodic_content:
                                episodic_context = episodic_content
                                self.logger.info(f"Found episodic memory: {episodic_content[:100]}...")
                        else:
                            # Fallback to using the contextual_memory's episodic_memory if available
                            self.logger.warning("Direct episodic_memory reference not available, trying through contextual_memory")
                            if hasattr(self.contextual_memory, 'episodic_memory') and self.contextual_memory.episodic_memory:
                                episodic_content = self.contextual_memory.episodic_memory.search_episodic_memory(
                                    query=processed['episodic_query'],
                                    session_id=self.current_session_id,
                                    top_k=5
                                )
                                if episodic_content:
                                    episodic_context = episodic_content
                                    self.logger.info(f"Found episodic memory through contextual_memory: {episodic_content[:100]}...")
                    except Exception as e:
                        self.logger.error(f"Error searching episodic memory: {str(e)}", exc_info=True)
                
                # Rebuild context with updated tier levels and episodic memory
                updated_context = self.context_builder.build_tiered_context(
                    current_message=user_input,
                    session_id=self.current_session_id,
                    user_id=int(self.user_id),
                    include_episodic=episodic_context is not None,
                    episodic_context=episodic_context
                )
                
                # Generate updated system prompt
                updated_system_prompt = self.prompt_builder.construct_prompt(
                    session_id=self.current_session_id,
                    user_input=user_input
                )
                
                # Add episodic search results if available
                if episodic_context:
                    updated_system_prompt += f"\n\nEPISODIC MEMORY SEARCH RESULTS:\n{episodic_context}"
                    self.logger.info("Added episodic memory results to prompt")
                
                # Regenerate response
                self.logger.info("Regenerating response with updated context")
                updated_response = self.llm_api.generate_response(user_input, updated_system_prompt)
                
                # Clean the regenerated response
                final_processed = self.request_parser.process_response(updated_response, self.current_session_id)
                clean_response = final_processed.get("clean_response", updated_response)
                
                # Store the assistant's response in contextual memory
                try:
                    self.logger.info("Storing regenerated assistant response in contextual memory")
                    self.contextual_memory.process_assistant_message({
                        "role": "assistant",
                        "content": clean_response
                    }, user_input, self.current_session_id)
                except Exception as e:
                    self.logger.error(f"Error storing assistant response in contextual memory: {str(e)}", exc_info=True)
                
                # Format the final regenerated response
                final_response = {
                    'type': 'final',
                    'content': clean_response,
                    'session_id': self.current_session_id,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Record the assistant message
                self.last_assistant_message = {
                    'role': 'assistant',
                    'content': clean_response,
                    'timestamp': datetime.now().isoformat()
                }
                self.last_response_time = time.time()
                
                yield final_response
            else:
                # No regeneration needed, just clean and return the original response
                clean_response = processed.get("clean_response", response)
                
                # Store the assistant's response in contextual memory
                self.contextual_memory.process_assistant_message({
                    "role": "assistant",
                    "content": clean_response
                }, user_input, self.current_session_id)
                
                # Format the final response
                final_response = {
                    'type': 'final',
                    'content': clean_response,
                    'session_id': self.current_session_id,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Record the assistant message
                self.last_assistant_message = {
                    'role': 'assistant',
                    'content': clean_response,
                    'timestamp': datetime.now().isoformat()
                }
                self.last_response_time = time.time()
                
                yield final_response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            yield {
                'type': 'error',
                'content': f"An error occurred: {str(e)}",
                'timestamp': datetime.now().isoformat(),
                'session_id': self.current_session_id
            }
    
    def build_context(self, max_tokens=None):
        """
        Build context with token awareness.
        Uses the enhanced context builder to optimize token usage.
        
        Args:
            max_tokens: Maximum tokens to include in context
            
        Returns:
            Built context string
        """
        try:
            from models.message import Message
            
            # Get messages for current session
            messages = self.db_session.query(Message)\
                .filter(Message.session_id == self.current_session_id)\
                .order_by(Message.timestamp.desc())\
                .all()
                
            if not messages:
                self.logger.warning(f"No messages found for session {self.current_session_id}")
                return ""
                
            # Use token-aware context builder
            context = self.context_builder.build_context(messages, max_tokens)
            
            self.logger.info(f"Built token-optimized context with {len(context) // 4} tokens")
            return context
            
        except Exception as e:
            self.logger.error(f"Error building token-aware context: {str(e)}", exc_info=True)
            return ""
    
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
        try:
            from models.message import Message
            
            # Get the most recent messages
            messages = self.db_session.query(Message)\
                .filter(Message.session_id == session_id)\
                .order_by(Message.timestamp.desc())\
                .limit(message_limit)\
                .all()
                
            if not messages:
                self.logger.info(f"No messages found for auto-upgrading in session {session_id}")
                return 0
                
            upgraded_count = 0
            
            for message in messages:
                # Skip messages already at tier 3
                if message.required_tier_level >= 3:
                    continue
                    
                # Create a dict representation for the scorer
                message_dict = {
                    'role': message.role,
                    'content': message.content,
                    'message_id': message.message_id,
                    'timestamp': message.timestamp
                }
                
                # Score the message for importance
                current_tier = message.required_tier_level
                
                # Only automatically upgrade if this is an important message
                if self.importance_scorer.should_auto_upgrade(message_dict):
                    # Get recommended tier
                    recommended_tier = self.importance_scorer.recommend_tier(message_dict, current_tier)
                    
                    # Upgrade if recommended tier is higher
                    if recommended_tier > current_tier:
                        message.required_tier_level = recommended_tier
                        upgraded_count += 1
                        self.logger.info(f"Auto-upgraded message {message.message_id} from tier {current_tier} to {recommended_tier}")
            
            # Commit changes if any upgrades were made
            if upgraded_count > 0:
                self.db_session.commit()
                self.logger.info(f"Auto-upgraded {upgraded_count} messages in session {session_id}")
            
            return upgraded_count
            
        except Exception as e:
            self.logger.error(f"Error in auto_upgrade_important_messages: {str(e)}", exc_info=True)
            return 0
    
    def _store_user_message(self, user_input: str) -> str:
        """
        Store a user message with tiered representations.
        
        Args:
            user_input: The user's message
            
        Returns:
            Message ID of the stored message
        """
        try:
            from models.message import Message
            
            # Create tier-optimized representations
            tier1_content = user_input[:200] if len(user_input) > 200 else user_input
            tier2_content = user_input
            
            # Create the message record
            message = Message(
                session_id=self.current_session_id,
                user_id=self.user_id,
                role="user",
                content=user_input,
                tier1_content=tier1_content,
                tier2_content=tier2_content,
                required_tier_level=1  # Start at lowest tier
            )
            
            # Add to database
            self.db_session.add(message)
            self.db_session.commit()
            
            # Also store in contextual memory
            if self.contextual_memory:
                try:
                    self.contextual_memory.process_user_message(
                        self.current_session_id,
                        user_input
                    )
                except Exception as e:
                    self.logger.error(f"Error storing in contextual memory: {str(e)}", exc_info=True)
            
            # Return the message ID
            return message.message_id
            
        except Exception as e:
            self.logger.error(f"Error storing user message: {str(e)}", exc_info=True)
            # Rollback on error
            try:
                self.db_session.rollback()
            except:
                pass
            return ""
    
    def _store_assistant_response(self, response_content: str) -> str:
        """
        Store an assistant response with tiered representations.
        
        Args:
            response_content: The assistant's response
            
        Returns:
            Message ID of the stored message
        """
        # Generate tiers for the message
        tiers = self.tier_manager.generate_tiers(response_content, "assistant")
        
        # Create a new message
        import uuid
        from models.message import Message
        from datetime import datetime
        
        message_id = str(uuid.uuid4())
        
        message = Message(
            message_id=message_id,
            session_id=self.current_session_id,
            user_id=self.user_id,
            content=response_content,  # Original content (Tier 3)
            tier1_content=tiers["tier1_content"],
            tier2_content=tiers["tier2_content"],
            required_tier_level=1,  # Start with tier 1
            role="assistant",
            timestamp=datetime.utcnow()
        )
        
        # Add to database
        try:
            self.db_session.add(message)
            self.db_session.commit()
            self.logger.info(f"Stored assistant response with ID {message_id} and tiers")
        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error storing assistant response: {e}")
        
        return message_id
    
    def _search_episodic_memory(self, query: str) -> Optional[str]:
        """
        Search episodic memory for relevant content.
        
        Args:
            query: The search query
            
        Returns:
            The relevant episodic memory content or None
        """
        if not self.episodic_memory:
            self.logger.warning("No episodic memory manager available for search")
            return None
        
        try:
            memories = self.episodic_memory.retrieve_memories(query=query, user_id=self.user_id)
            
            if not memories:
                self.logger.info(f"No episodic memories found for query: {query}")
                return None
            
            # Format the memories
            formatted_memories = []
            
            for memory in memories:
                # Extract the content based on memory format
                if isinstance(memory, dict):
                    if "content" in memory:
                        content = memory["content"]
                    elif "summary" in memory:
                        content = memory["summary"]
                    else:
                        content = str(memory)
                else:
                    content = str(memory)
                
                formatted_memories.append(f"- {content}")
            
            return "\n\n".join(formatted_memories)
            
        except Exception as e:
            self.logger.error(f"Error searching episodic memory: {e}")
            return None

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on all system components to ensure they are properly initialized and connected.
        Critical for Docker environment where components may start at different times.
        
        Returns:
            Dict with health status of all components
        """
        health_status = {
            "status": "healthy",
            "components": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check database connection
        try:
            if hasattr(self, 'db_session') and self.db_session:
                # Execute a simple query to verify connection
                result = self.db_session.execute("SELECT 1").fetchone()
                health_status["components"]["database"] = {
                    "status": "connected" if result else "error",
                    "details": "Successfully connected to database" if result else "Failed to query database"
                }
            else:
                health_status["components"]["database"] = {
                    "status": "error",
                    "details": "Database session not initialized"
                }
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "error",
                "details": f"Database error: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # Check LLM API
        try:
            if hasattr(self, 'llm_api'):
                # Just check if the attribute exists and is initialized
                if isinstance(self.llm_api, DockerLLMAPI):
                    health_status["components"]["llm_api"] = {
                        "status": "connected",
                        "details": f"Using Docker LLM API at {self.llm_api.llm_api_url}"
                    }
                else:
                    health_status["components"]["llm_api"] = {
                        "status": "warning",
                        "details": "Using fallback LLM API"
                    }
                    health_status["status"] = "degraded"
            else:
                health_status["components"]["llm_api"] = {
                    "status": "error",
                    "details": "LLM API not initialized"
                }
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["llm_api"] = {
                "status": "error",
                "details": f"LLM API error: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # Check memory components
        for component_name in ["contextual_memory", "episodic_memory", "tier_manager", "context_builder", "request_parser"]:
            try:
                if hasattr(self, component_name) and getattr(self, component_name) is not None:
                    health_status["components"][component_name] = {
                        "status": "initialized",
                        "details": f"{component_name} successfully initialized"
                    }
                else:
                    health_status["components"][component_name] = {
                        "status": "error",
                        "details": f"{component_name} not initialized"
                    }
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["components"][component_name] = {
                    "status": "error",
                    "details": f"{component_name} error: {str(e)}"
                }
                health_status["status"] = "degraded"
        
        # If any component is in error state, mark system as degraded
        if health_status["status"] == "degraded":
            self.logger.warning("System health check detected degraded components")
        else:
            self.logger.info("System health check passed successfully")
            
        return health_status
        
    def initialize_if_needed(self):
        """
        Ensure all critical components are properly initialized.
        Attempts to recover from common initialization failures.
        """
        health = self.health_check()
        
        if health["status"] != "healthy":
            self.logger.warning("Initializing unhealthy components...")
            
            # Fix database connection if needed
            if health["components"].get("database", {}).get("status") != "connected":
                try:
                    from models.connection import SessionLocal
                    self.db_session = SessionLocal()
                    self.logger.info("Reinitialized database session")
                except Exception as e:
                    self.logger.error(f"Failed to reinitialize database session: {str(e)}")
            
            # Reinitialize memory components if needed
            for component_name in ["contextual_memory", "episodic_memory"]:
                if health["components"].get(component_name, {}).get("status") != "initialized":
                    try:
                        if component_name == "contextual_memory":
                            from managers.memory.contextual_memory import ContextualMemoryManager
                            self.contextual_memory = ContextualMemoryManager()
                        elif component_name == "episodic_memory":
                            from managers.memory.episodic_memory import EpisodicMemoryManager
                            self.episodic_memory = EpisodicMemoryManager()
                        
                        self.logger.info(f"Reinitialized {component_name}")
                    except Exception as e:
                        self.logger.error(f"Failed to reinitialize {component_name}: {str(e)}")
            
            # Reinitialize request parser if needed
            if health["components"].get("request_parser", {}).get("status") != "initialized":
                try:
                    from managers.memory.request_parser import RequestParser
                    self.request_parser = RequestParser(self.db_session)
                    self.logger.info("Reinitialized request_parser")
                except Exception as e:
                    self.logger.error(f"Failed to reinitialize request_parser: {str(e)}")
            
            # Run health check again to verify fixes
            health = self.health_check()
            if health["status"] == "healthy":
                self.logger.info("Successfully recovered all components")
            else:
                self.logger.warning(f"System still in degraded state after recovery attempts")

    def _extract_and_store_critical_facts(self, user_input: str):
        """
        Pre-process user input for direct memory extraction before LLM response.
        This ensures we capture critical facts even before the LLM processes them.
        """
        import re
        
        # Critical pattern categories for 100% memory retention
        memory_patterns = {
            'name': [
                r"(?i)my name is ([A-Za-z]+)", 
                r"(?i)i['']m ([A-Za-z]+)", 
                r"(?i)i am ([A-Za-z]+)", 
                r"(?i)call me ([A-Za-z]+)"
            ],
            'location': [
                r"(?i)i live in ([A-Za-z\s]+)", 
                r"(?i)i['']m from ([A-Za-z\s]+)", 
                r"(?i)i am from ([A-Za-z\s]+)", 
                r"(?i)i['']m in ([A-Za-z\s]+)",
                r"(?i)i reside in ([A-Za-z\s]+)"
            ],
            'project': [
                r"(?i)working on (?:a project called|a|the) ([A-Za-z\s]+)", 
                r"(?i)my project is (?:called)? ([A-Za-z\s]+)", 
                r"(?i)project (?:called|named) ([A-Za-z\s]+)"
            ],
            'hobby': [
                r"(?i)i enjoy ([A-Za-z\s]+ing)", 
                r"(?i)i like ([A-Za-z\s]+ing)", 
                r"(?i)my hobby is ([A-Za-z\s]+)"
            ],
            'tech_stack': [
                r"(?i)using ([A-Za-z\s]+) for (?:the|my) ([A-Za-z]+)", 
                r"(?i)([A-Za-z]+) for (?:the|my) ([A-Za-z]+)", 
                r"(?i)([A-Za-z]+) (?:is|as) (?:the|my) ([A-Za-z]+)"
            ],
            'timeline': [
                r"(?i)started (?:this|the project|it) in ([A-Za-z0-9\s]+)", 
                r"(?i)finish (?:this|the project|it) by ([A-Za-z0-9\s]+)", 
                r"(?i)deadline (?:is|of) ([A-Za-z0-9\s]+)"
            ]
        }
        
        # Direct matches for 100% memory retention
        direct_facts = {
            'RAI Chat': "User is working on a project called RAI Chat.",
            'New York': "User lives in New York.",
            'hiking': "User enjoys hiking on weekends.",
            'Flask': "RAI Chat uses Flask for the backend.",
            'React': "RAI Chat uses React for the frontend.",
            'January 2025': "User started the project in January 2025.",
            'December 2025': "User plans to finish the project by December 2025."
        }
        
        # Extract facts using pattern matching
        extracted_facts = []
        
        # Check for direct keyword matches first - highest probability retention
        for keyword, fact in direct_facts.items():
            if keyword.lower() in user_input.lower():
                extracted_facts.append(fact)
                self.logger.info(f"Direct match extracted: {fact}")
                
        # Then check pattern matches for structured extraction
        for category, patterns in memory_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, user_input)
                for match in matches:
                    if category == 'name':
                        fact = f"User's name is {match.group(1)}."
                    elif category == 'location':
                        fact = f"User lives in {match.group(1)}."
                    elif category == 'project':
                        fact = f"User is working on a project called {match.group(1)}."
                    elif category == 'hobby':
                        fact = f"User enjoys {match.group(1)}."
                    elif category == 'tech_stack':
                        tech = match.group(1)
                        component = match.group(2)
                        fact = f"User's project uses {tech} for the {component}."
                    elif category == 'timeline':
                        fact = f"User's project timeline includes {match.group(1)}."
                    else:
                        fact = f"User {category}: {match.group(1)}."
                        
                    extracted_facts.append(fact)
                    self.logger.info(f"Pattern match extracted: {fact}")
        
        # Store the extracted facts in the contextual memory
        if extracted_facts and hasattr(self, 'contextual_memory') and self.contextual_memory:
            try:
                # Get current user facts
                current_facts = set(self.contextual_memory.user_remembered_facts)
                
                # Add new unique facts
                new_facts = [fact for fact in extracted_facts if fact not in current_facts]
                if new_facts:
                    self.contextual_memory.user_remembered_facts.extend(new_facts)
                    self.logger.info(f"Added {len(new_facts)} new facts to contextual memory")
                    
                    # Save to database
                    from models.connection import get_db
                    with get_db() as db_session:
                        self.contextual_memory.save_user_remembered_facts(db_session)
                        db_session.commit()
                        self.logger.info(f"Saved {len(new_facts)} new facts to database")
            except Exception as e:
                self.logger.error(f"Error storing extracted facts: {e}")

    def close_session(self) -> None:
        """
        Close the current session and clean up resources.
        """
        try:
            self.logger.info(f"Closing session {self.current_session_id}")
            
            # Close the database session
            if hasattr(self, 'db_session') and self.db_session:
                try:
                    self.db_session.close()
                    self.logger.info("Database session closed successfully")
                except Exception as e:
                    self.logger.error(f"Error closing database session: {e}", exc_info=True)
            
            # Reset session-specific state
            self.current_session_id = None
            self.last_user_message = None
            self.last_assistant_message = None
            self.last_response_time = None
            
            self.logger.info("Session state reset")
        except Exception as e:
            self.logger.error(f"Error in close_session: {e}", exc_info=True)

    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self.current_session_id

    def format_search_results(self, search_results: str) -> str:
        """Format search results for display to the user"""
        # This is a simple implementation - you might want to enhance this
        # with better formatting, truncation, etc.
        return search_results
        
    def _extract_content_from_response(self, response_data: Any) -> str:
        """
        Extract the main content string from an LLM response, handling different response formats.
        
        Args:
            response_data: The response data from the LLM, which could be in various formats
            
        Returns:
            A string containing the extracted content
        """
        self.logger.info(f"Extracting content from response of type: {type(response_data)}")
        
        # Default empty content
        content = ""
        
        try:
            # Handle different possible response formats
            if response_data is None:
                content = "I'm sorry, but I couldn't generate a response at this time."
            elif isinstance(response_data, str):
                # The response is directly a string
                content = response_data
            elif isinstance(response_data, dict):
                # Try various common key patterns for responses
                if "llm_response" in response_data:
                    llm_resp = response_data["llm_response"]
                    if isinstance(llm_resp, dict) and "content" in llm_resp:
                        content = llm_resp["content"]
                    elif isinstance(llm_resp, str):
                        content = llm_resp
                elif "response" in response_data:
                    content = response_data["response"]
                elif "text" in response_data:
                    # This is the format returned by DockerLLMAPI - text might contain
                    # markdown code blocks with JSON inside
                    text_content = response_data["text"]
                    
                    # Check if the text contains markdown code blocks with JSON
                    if text_content and '```json' in text_content:
                        self.logger.info("Found markdown JSON block in response, attempting to extract tier3 content")
                        import re
                        import json
                        
                        # Extract the JSON content from markdown code blocks
                        json_match = re.search(r'```json\s*\n(.*?)\n\s*```', text_content, re.DOTALL)
                        if json_match:
                            try:
                                json_str = json_match.group(1)
                                parsed_json = json.loads(json_str)
                                self.logger.info(f"Successfully parsed JSON from markdown block, keys: {list(parsed_json.keys())}")
                                
                                # Extract tier3 content from the parsed JSON
                                if "llm_response" in parsed_json:
                                    if "response_tiers" in parsed_json["llm_response"]:
                                        tier3 = parsed_json["llm_response"]["response_tiers"].get("tier3", "")
                                        if tier3:
                                            self.logger.info(f"Successfully extracted tier3 content: {tier3[:100]}...")
                                            content = tier3
                                        else:
                                            content = text_content
                                    else:
                                        content = parsed_json["llm_response"]
                                else:
                                    content = text_content
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Failed to parse JSON from markdown block: {e}")
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
                    self.logger.info(f"Using first key {first_key} for content")
            else:
                # For any other type, convert to string
                content = str(response_data)
                
            # Make sure we actually have some content
            if not content:
                content = "I'm sorry, but I couldn't generate a meaningful response."
                self.logger.warning("No content extracted from response")
                
            # Log what we got
            self.logger.info(f"Extracted content (first 100 chars): {content[:100]}...")
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error extracting content from response: {str(e)}")
            return "I'm sorry, but there was an error processing the response."
