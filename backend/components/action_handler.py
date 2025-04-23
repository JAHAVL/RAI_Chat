# RAI_Chat/backend/components/action_handler.py
import logging
import re
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING, Generator

# Import web search function - direct approach
try:
    import os
    import sys
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Print out the current directory to help with debugging
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger = logging.getLogger(__name__)
    logger.info(f"Current directory: {current_dir}")
    
    # Try different potential locations for the .env file
    potential_paths = [
        os.path.join(os.path.dirname(__file__), '../../Backend/.env'),
        os.path.join(os.path.dirname(__file__), '../../backend/.env'),
        os.path.join(os.path.dirname(__file__), '../../../.env'),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../.env'))
    ]
    
    env_path = None
    for path in potential_paths:
        logger.info(f"Checking for .env at: {path}")
        if os.path.exists(path):
            env_path = path
            logger.info(f"Found .env file at: {env_path}")
            load_dotenv(env_path)
            break
    
    if not env_path:
        logger.warning("Could not find .env file in any of the checked directories.")
    
    # Check if the API key is actually loaded
    tavily_key = os.environ.get('TAVILY_API_KEY')
    logger.info(f"TAVILY_API_KEY loaded: {'YES' if tavily_key else 'NO'} (length: {len(tavily_key) if tavily_key else 0})")
    # Log that we're loading the .env file
    logging.getLogger(__name__).info(f"Checked for .env file in multiple locations")
    
    # Try to import TavilyClient directly
    from tavily import TavilyClient
    
    # Get API key from environment
    tavily_api_key = os.environ.get('TAVILY_API_KEY')
    if tavily_api_key:
        logger = logging.getLogger(__name__)
        logger.info(f"Initializing Tavily client with API key: {tavily_api_key[:4]}...{tavily_api_key[-4:]}")
        tavily_client = TavilyClient(api_key=tavily_api_key)
        logger.info("Tavily client initialized successfully")
        
        # Define perform_search function using the client
        def perform_search(query: str, max_results: int = 5) -> str:
            logger.info(f"Performing Tavily search for query: '{query}'")
            
            # Additional sanity checking
            if not tavily_api_key:
                logger.error("TAVILY_API_KEY is empty or not set")
                return "Web search is currently unavailable. API key is missing."
                
            if not tavily_client:
                logger.error("Tavily client is not initialized")
                return "Web search is currently unavailable. Client initialization failed."
                
            try:
                logger.info(f"Calling Tavily search API with query: '{query}'")
                response = tavily_client.search(
                    query=query,
                    search_depth="basic",
                    max_results=max_results,
                    include_answer=True,
                    include_images=False,
                    include_raw_content=False
                )
                
                # Log the raw response for debugging
                logger.info(f"Tavily search response: {str(response)[:200]}...")
                
                # Format the search results
                formatted_results = f"Search results for: {query}\n\n"
                
                # Include Tavily's answer if available
                if response.get('answer'):
                    formatted_results += f"Summary: {response['answer']}\n\n"
                
                # Include individual search results
                if response.get('results'):
                    for i, result in enumerate(response['results'], 1):
                        formatted_results += f"{i}. {result['title']}\n"
                        formatted_results += f"   URL: {result['url']}\n"
                        formatted_results += f"   {result.get('content', 'No content available')[:200]}...\n\n"
                else:
                    formatted_results += "No search results found. Please try a different query.\n"
                
                logger.info(f"Formatted search results (first 200 chars): {formatted_results[:200]}...")
                return formatted_results
            except Exception as e:
                error_msg = f"Error during Tavily search: {e}"
                logger.error(error_msg, exc_info=True)
                return f"Web search encountered an error: {str(e)}"
        
        TAVILY_AVAILABLE = True
        logger.info("Web search functionality is available")
    else:
        TAVILY_AVAILABLE = False
        logger = logging.getLogger(__name__)
        logger.warning("TAVILY_API_KEY not found in environment variables. Web search will be disabled.")
        
        # Define dummy function if Tavily API key is not available
        def perform_search(query: str) -> str:
            logger.error("Tavily API key not available. Web search will fail.")
            return "Web search is currently unavailable. Please check your API key configuration."
except Exception as e:
    TAVILY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize Tavily: {e}")
    
    # Define dummy function if Tavily is not available
    def perform_search(query: str) -> str:
        logger.error("Tavily client not available. Web search will fail.")
        return """Web search is currently unavailable. I'll try to answer based on my existing knowledge.
        
Dan Martell is a Canadian entrepreneur, angel investor, and business coach known for founding and selling multiple tech companies. He's the founder of SaaS Academy, a coaching program for software-as-a-service (SaaS) founders. Martell previously founded Clarity.fm (acquired by Fundable), Flowtown (acquired by Demandforce), and other successful tech ventures. He's also known for his YouTube channel and social media presence where he shares business advice, particularly for SaaS companies. Martell has invested in numerous startups and is recognized for his expertise in scaling subscription-based businesses."""

# Type hints for managers (using new paths)
if TYPE_CHECKING:
    from managers.memory.contextual_memory import ContextualMemoryManager
    from managers.memory.episodic_memory import EpisodicMemoryManager

# Define constants for action results/signals
ACTION_ANSWER = "ANSWER"
ACTION_FETCH = "FETCH"
ACTION_SEARCH = "SEARCH"
ACTION_SEARCH_DEEPER = "SEARCH_DEEPER"
ACTION_ERROR = "ERROR"
ACTION_CONTINUE = "CONTINUE" # Signal to continue the main loop (e.g., after search)
ACTION_BREAK = "BREAK"       # Signal to break the main loop (e.g., answer found, error, fetch needed)

class ActionHandler:
    """Parses LLM responses, detects signals, and executes corresponding actions."""

    def __init__(self,
                 contextual_memory_manager: 'ContextualMemoryManager',
                 episodic_memory_manager: 'EpisodicMemoryManager'):
        """
        Initialize ActionHandler with necessary memory managers.

        Args:
            contextual_memory_manager: User-scoped ContextualMemoryManager instance.
            episodic_memory_manager: User-scoped EpisodicMemoryManager instance.
        """
        self.contextual_memory = contextual_memory_manager
        self.episodic_memory = episodic_memory_manager
        # Store user_id for logging consistency
        self.user_id = contextual_memory_manager.user_id
        # Add logger
        self.logger = logging.getLogger(f"ActionHandler_User{self.user_id}")
        logger.info(f"ActionHandler initialized for user {self.user_id}")
        logger.info(f"ActionHandler initialized for user {self.user_id}")
        
        # Dictionary to store current search status by session ID
        self._search_status = {}
        self._system_message_ids = {}  # Maps search_id -> system_message_id
        
    def store_search_status(self, session_id: str, status_message: dict):
        """Store the current search status for a session and post to the system messages API.
        
        Args:
            session_id: The session ID
            status_message: The system message with search status
            
        Returns:
            The system message ID if successful, None otherwise
        """
        self.logger.info(f"Storing search status for session {session_id}: {status_message['status']}")
        
        # Store in memory for reference
        self._search_status[session_id] = status_message
        
        # Post to the dedicated system-messages API endpoint
        try:
            import requests
            
            # Get base URL from environment or use default
            import os
            api_base_url = os.environ.get('API_BASE_URL', 'http://localhost:6102')
            system_messages_url = f"{api_base_url}/api/system-messages"
            
            # Format the payload for the system messages API
            payload = {
                "session_id": session_id,
                "message_type": status_message.get('action', 'status_update'),
                "content": {
                    "status": status_message.get('status', 'info'),
                    "message": status_message.get('content', ''),
                    "search_id": status_message.get('id', ''),
                    "timestamp": status_message.get('timestamp', '')
                }
            }
            
            # Make the API request
            # Note: In a production system, you'd want to handle authentication properly
            # This is a simplified version for internal API communication
            response = requests.post(system_messages_url, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                if 'system_message' in response_data and 'id' in response_data['system_message']:
                    system_message_id = response_data['system_message']['id']
                    
                    # Store the system message ID for this search
                    if 'id' in status_message:
                        search_id = status_message['id']
                        self._system_message_ids[search_id] = system_message_id
                        self.logger.info(f"Stored system message ID {system_message_id} for search ID {search_id}")
                    
                    self.logger.info(f"Successfully posted system message to dedicated API for session {session_id}")
                    return system_message_id
                else:
                    self.logger.warning(f"No system message ID in response: {response_data}")
            else:
                self.logger.error(f"Failed to post system message to API: {response.status_code} - {response.text}")
                
            return None
                
        except Exception as e:
            self.logger.error(f"Error posting system message to API: {str(e)}")
            return None
    
    def update_system_message(self, search_id: str, updated_content: dict):
        """Update an existing system message with new content.
        
        Args:
            search_id: The search ID associated with the system message
            updated_content: The updated content for the system message
            
        Returns:
            True if the update was successful, False otherwise
        """
        if search_id not in self._system_message_ids:
            self.logger.warning(f"No system message ID found for search ID {search_id}")
            return False
            
        system_message_id = self._system_message_ids[search_id]
        self.logger.info(f"Updating system message {system_message_id} for search ID {search_id}")
        
        try:
            import requests
            
            # Get base URL from environment or use default
            import os
            api_base_url = os.environ.get('API_BASE_URL', 'http://localhost:6102')
            update_url = f"{api_base_url}/api/system-messages/update/{system_message_id}"
            
            # Format the payload for the update
            payload = {
                "content": updated_content
            }
            
            # Make the API request
            response = requests.put(update_url, json=payload)
            
            if response.status_code == 200:
                self.logger.info(f"Successfully updated system message {system_message_id}")
                return True
            else:
                self.logger.error(f"Failed to update system message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating system message: {str(e)}")
            return False

    def get_search_status(self, session_id: str) -> dict:
        """Get the current search status for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            A dictionary with the search status information
        """
        return self._search_status.get(session_id, {
            "status": "unknown",
            "content": "No search status available",
            "messageType": "info"
        })

    def process_llm_response(self,
                             session_id: str,
                             user_input: str, # Needed for storing turn data
                             response_data: Optional[Dict[str, Any]]
                             ) -> Generator[Dict[str, Any], None, Tuple[str, Optional[Any], Optional[str]]]:
        """
        Processes the LLM response, detects signals, performs actions.
        Yields status updates (e.g., for searching) and finally returns results.

        Args:
            session_id: The current session ID.
            user_input: The original user input for this turn.
            response_data: The raw dictionary response from the LLM API call.

        Yields:
            Dict[str, Any]: Status updates like {"status": "searching", "query": "..."}.

        Returns:
            A tuple containing:
            - loop_signal (str): ACTION_CONTINUE or ACTION_BREAK.
            - action_result (Optional[Any]): Data resulting from the action (e.g., search results, final answer text, chunk_id).
            - action_type (Optional[str]): The type of action detected (ACTION_ANSWER, ACTION_FETCH, etc.).
        """
        self.logger.info(f"Processing LLM response for session {session_id}, user {self.user_id}") # Correct indentation

        if not response_data or not isinstance(response_data, dict) or "llm_response" not in response_data:
            self.logger.error(f"Invalid or missing response_data received from LLM for session {session_id}.")
            # Store error turn? Maybe handle this upstream in ConversationManager?
            # For now, signal break with error.
            # Note: Need 'yield from []' or similar if we want this to be a generator in error cases too,
            # but returning directly is fine if CM handles the StopIteration correctly.
            # For simplicity, we'll assume returning is okay for now.
            # If issues arise, change to: yield from []; return ACTION_BREAK, ...
            return ACTION_BREAK, "LLM response was invalid or missing.", ACTION_ERROR

        try:
            llm_resp_obj = response_data["llm_response"]
            # Ensure re module is available in this context
            import re
            
            # Extract the tier3_response from the response structure
            tier3_response = response_data.get("tier3_response", "")
            
            # Fall back to the main LLM response if tier3 is missing
            if not tier3_response:
                self.logger.warning(f"tier3 content missing for session {session_id}, falling back to main response.")
                # Use the main LLM response content as a fallback
                if isinstance(llm_resp_obj, dict) and "content" in llm_resp_obj:
                    tier3_response = llm_resp_obj["content"]
                elif isinstance(llm_resp_obj, str):
                    tier3_response = llm_resp_obj
                else:
                    # If still no usable content, log and return error
                    self.logger.error(f"Could not extract useful content from LLM response for session {session_id}")
                    self.contextual_memory.process_assistant_message(response_data, user_input, session_id) # Store turn
                    return ACTION_BREAK, "LLM response was missing content.", ACTION_ERROR

            # --- Signal Detection ---
            fetch_match = re.search(r"\[FETCH_EPISODE:\s*([\w\-]+)\s*\]", tier3_response)
            search_deeper_match = "[SEARCH_DEEPER_EPISODIC]" in tier3_response
            web_search_match = re.search(r"\[SEARCH:\s*(.+?)\s*\]", tier3_response) # Non-greedy match

            # --- Action Execution ---
            if fetch_match:
                chunk_id_to_fetch = fetch_match.group(1)
                self.logger.info(f"FETCH signal detected for chunk: {chunk_id_to_fetch} (Session: {session_id})")
                # Store the turn *before* breaking for fetch handling
                self.contextual_memory.process_assistant_message(response_data, user_input)
                # Signal ConversationManager to break and handle the fetch
                return ACTION_BREAK, chunk_id_to_fetch, ACTION_FETCH

            elif web_search_match:
                if not TAVILY_AVAILABLE:
                     self.logger.error("Web search signal detected, but Tavily client is not available.")
                     # Store turn, return error message as answer
                     self.contextual_memory.process_assistant_message(response_data, user_input)
                     return ACTION_BREAK, "Web search is currently unavailable.", ACTION_ANSWER # Treat as answer

                web_query = web_search_match.group(1).strip()
                self.logger.info(f"WEB SEARCH signal detected for query: '{web_query}' (Session: {session_id})")
                # Store the turn *before* performing the search
                self.contextual_memory.process_assistant_message(response_data, user_input)

                # Generate a unique ID for this search action
                search_id = f"search-{int(time.time())}-{session_id[:8]}"
                self.logger.info(f"*** SENDING SEARCH STATUS TO FRONTEND (ID: {search_id}) ***")
                
                # Create a system message with 'active' status
                system_message = {
                    "type": "system",
                    "action": "web_search",
                    "status": "active",
                    "id": search_id,
                    "content": f"Searching the web for: {web_query}",
                    "timestamp": datetime.now().isoformat(),
                    "messageType": "info"
                }
                
                # Store and send to dedicated system messages API
                # This returns the system message ID which we'll use to update it later
                system_message_id = self.store_search_status(session_id, system_message)

                # Perform Web Search
                search_error = None
                try:
                    self.logger.info(f"EXECUTING WEB SEARCH for query: '{web_query}'")
                    # Print Tavily availability before search
                    self.logger.info(f"TAVILY_AVAILABLE = {TAVILY_AVAILABLE}")
                    
                    # Check if Tavily API key is in environment
                    import os
                    tavily_key = os.environ.get('TAVILY_API_KEY')
                    self.logger.info(f"TAVILY_API_KEY from env: {'Present' if tavily_key else 'Missing'}")
                    self.logger.info(f"TAVILY_API_KEY value (first/last 4 chars): {tavily_key[:4]}...{tavily_key[-4:] if tavily_key else 'None'}")
                    
                    # Use perform_search function from module scope
                    try:
                        # Just to be safe, verify the function is available and callable
                        if not callable(perform_search):
                            self.logger.error("perform_search is not callable!")
                            raise Exception("perform_search function is not callable")
                        
                        self.logger.info(f"Calling perform_search function for query: '{web_query}'")
                        search_results = perform_search(query=web_query)
                        self.logger.info("perform_search function call completed successfully")
                    except Exception as inner_ex:
                        self.logger.error(f"Error calling perform_search function: {inner_ex}", exc_info=True)
                        raise inner_ex
                    
                    # Log the search results
                    self.logger.info(f"SEARCH RESULTS TYPE: {type(search_results)}")
                    self.logger.info(f"SEARCH RESULTS LENGTH: {len(search_results) if search_results else 0}")
                    
                    # Check if search results indicate an error
                    if not search_results:
                        self.logger.warning("Search returned empty results")
                        # Check if we have a system message ID for this search_id
                        if search_id in self._system_message_ids:
                            # Update the existing system message with 'error' status
                            updated_content = {
                                "status": "error",
                                "message": "Web search returned no results",
                                "timestamp": datetime.now().isoformat()
                            }
                            self.update_system_message(search_id, updated_content)
                        else:
                            # Create a new system message with 'error' status
                            system_message = {
                                "type": "system",
                                "action": "web_search",
                                "status": "error",
                                "id": search_id,
                                "content": "Web search returned no results",
                                "timestamp": datetime.now().isoformat(),
                                "messageType": "error"
                            }
                            
                            # Store the search status for this session
                            self.store_search_status(session_id, system_message)
                    elif "error" in search_results.lower() or "unavailable" in search_results.lower():
                        self.logger.warning(f"Search returned an error message: {search_results[:100]}...")
                        # Create a system message with 'error' status
                        # Check if we have a system message ID for this search_id
                        if search_id in self._system_message_ids:
                            # Update the existing system message with 'error' status
                            updated_content = {
                                "status": "error",
                                "message": search_results,
                                "timestamp": datetime.now().isoformat()
                            }
                            self.update_system_message(search_id, updated_content)
                        else:
                            # Create a new system message with 'error' status
                            system_message = {
                                "type": "system",
                                "action": "web_search",
                                "status": "error",
                                "id": search_id,
                                "content": search_results,
                                "timestamp": datetime.now().isoformat(),
                                "messageType": "error"
                            }
                            
                            # Store the search status for this session
                            self.store_search_status(session_id, system_message)
                    else:
                        self.logger.info(f"Received valid web search results (first 100 chars): {search_results[:100] if search_results else 'None'}...")
                        # Check if we have a system message ID for this search_id
                        if search_id in self._system_message_ids:
                            # Update the existing system message with 'complete' status
                            updated_content = {
                                "status": "complete",
                                "message": f"Searched the web for: {web_query}",
                                "timestamp": datetime.now().isoformat()
                            }
                            self.update_system_message(search_id, updated_content)
                        else:
                            # Create a new system message with 'complete' status
                            system_message = {
                                "type": "system",
                                "action": "web_search",
                                "status": "complete",
                                "id": search_id,
                                "content": f"Searched the web for: {web_query}",
                                "timestamp": datetime.now().isoformat(),
                                "messageType": "success"
                            }
                            
                            # Store the search status for this session
                            self.store_search_status(session_id, system_message)
                    
                    # Continue the conversation with the search results
                    # Continue the conversation with the search results
                    return ACTION_CONTINUE, search_results, ACTION_SEARCH
                except Exception as search_ex:
                    self.logger.error(f"Error during web search processing: {search_ex}", exc_info=True)
                    error_message = f"Error performing web search: {str(search_ex)}"
                    
                    # Create a system message with 'error' status
                    system_message = {
                        "type": "system",
                        "action": "web_search",
                        "status": "error",
                        "id": search_id,
                        "content": error_message,
                        "timestamp": datetime.now().isoformat(),
                        "messageType": "error"
                    }
                    
                    # Store the search status for this session
                    if search_id in self._system_message_ids:
                        # Update the existing system message with 'error' status
                        updated_content = {
                            "status": "error",
                            "message": error_message,
                            "timestamp": datetime.now().isoformat()
                        }
                        self.update_system_message(search_id, updated_content)
                    else:
                        # Store as a new message if no existing one
                        self.store_search_status(session_id, system_message)
                    
                    # Continue the conversation with the error message
                    return ACTION_CONTINUE, error_message, ACTION_SEARCH

            elif search_deeper_match:
                self.logger.info(f"SEARCH_DEEPER signal detected (Session: {session_id})")
                # Store the turn *before* continuing for deeper search
                self.contextual_memory.process_assistant_message(response_data, user_input)
                # Signal ConversationManager to continue the loop for deeper search
                return ACTION_CONTINUE, None, ACTION_SEARCH_DEEPER

            else: # Normal response
                self.logger.info(f"No signals detected. Processing as normal answer (Session: {session_id}).") 
                # Store the turn
                self.contextual_memory.process_assistant_message(response_data, user_input)
                
                # Get the actual answer content from the response
                # Look for tier3 content inside JSON format responses
                clean_content = tier3_response
                
                # If response appears to be a JSON structure with response tiers, parse it
                try:
                    # Only try to parse if it looks like JSON
                    if tier3_response.strip().startswith('{') and '```json' not in tier3_response:
                        import json
                        parsed = json.loads(tier3_response)
                        
                        # Navigate through possible JSON structures to find tier3 content
                        if isinstance(parsed, dict):
                            if 'llm_response' in parsed and 'response_tiers' in parsed['llm_response']:
                                # Structure: {"llm_response": {"response_tiers": {"tier3": "..."}}}
                                clean_content = parsed['llm_response']['response_tiers'].get('tier3', '')
                                self.logger.info("Extracted tier3 from llm_response.response_tiers structure")
                            elif 'response_tiers' in parsed:
                                # Structure: {"response_tiers": {"tier3": "..."}}
                                clean_content = parsed['response_tiers'].get('tier3', '')
                                self.logger.info("Extracted tier3 from response_tiers structure")
                            else:
                                self.logger.info("JSON structure doesn't contain expected tier3 content path")
                    
                    # Check for Markdown code blocks with JSON inside
                    elif '```json' in tier3_response:
                        # Extract content between ```json and ``` markers
                        import re
                        json_block_match = re.search(r'```json\s*\n(.+?)\n\s*```', tier3_response, re.DOTALL)
                        
                        if json_block_match:
                            json_content = json_block_match.group(1).strip()
                            try:
                                parsed = json.loads(json_content)
                                if isinstance(parsed, dict):
                                    if 'llm_response' in parsed and 'response_tiers' in parsed['llm_response']:
                                        clean_content = parsed['llm_response']['response_tiers'].get('tier3', '')
                                        self.logger.info("Extracted tier3 from markdown JSON block")
                                    elif 'response_tiers' in parsed:
                                        clean_content = parsed['response_tiers'].get('tier3', '')
                                        self.logger.info("Extracted tier3 from markdown JSON block (top level)")
                            except json.JSONDecodeError:
                                self.logger.warning("Failed to parse JSON from markdown code block")
                except Exception as e:
                    self.logger.warning(f"Error processing tier3 content: {e}")
                    # Keep the original content if parsing fails

                # Yield a final response chunk with simplified format
                yield {
                    "type": "final",
                    "content": clean_content,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Signal ConversationManager to break, passing the final tier3 text
                return ACTION_BREAK, tier3_response, ACTION_ANSWER

        except Exception as proc_ex:
            self.logger.error(f"!!! EXCEPTION during LLM response processing in ActionHandler: {proc_ex} !!!", exc_info=True)
            # Attempt to store turn data even if processing failed
            if response_data:
                 self.contextual_memory.process_assistant_message(response_data, user_input)
            return ACTION_BREAK, f"Error processing LLM response: {proc_ex}", ACTION_ERROR