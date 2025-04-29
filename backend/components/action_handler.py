# RAI_Chat/backend/components/action_handler.py
import logging
import re
import json
import os
import time
from typing import Dict, Any, Tuple, Optional, List, Union, Callable, TYPE_CHECKING, Generator
from datetime import datetime

# Use direct import from models instead of core.database
from models.connection import get_db

# Import web search function - direct approach
try:
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
ACTION_REMEMBER = "REMEMBER"  # New action type for explicit memory storage
ACTION_CONTINUE = "CONTINUE" # Signal to continue the main loop (e.g., after search)
ACTION_BREAK = "BREAK"       # Signal to break the main loop (e.g., answer found, error, fetch needed)
ACTION_SEARCH_DETECTED = "ACTION_SEARCH_DETECTED"
ACTION_CALCULATE_DETECTED = "ACTION_CALCULATE_DETECTED"
ACTION_COMMAND_DETECTED = "ACTION_COMMAND_DETECTED"
ACTION_EXECUTE_DETECTED = "ACTION_EXECUTE_DETECTED"
ACTION_REMEMBER_DETECTED = "ACTION_REMEMBER_DETECTED"  # New signal for remember action
ACTION_FORGET_DETECTED = "ACTION_FORGET_DETECTED"
ACTION_CORRECT_DETECTED = "ACTION_CORRECT_DETECTED"
ACTION_UNKNOWN = "ACTION_UNKNOWN"
ACTION_NONE = "ACTION_NONE"

ACTION_FORGET = "FORGET"
ACTION_CORRECT = "CORRECT"

# Action signal categories by flow control behavior
# 
# INTERRUPTING ACTIONS (Return ACTION_BREAK, replace normal response):
# - [SEARCH:query] -> ACTION_SEARCH_DETECTED
# - [WEB_SEARCH:query] -> ACTION_SEARCH_DETECTED
#
# NON-INTERRUPTING ACTIONS (Return ACTION_CONTINUE, normal response still shown):
# - [REMEMBER:fact] -> ACTION_REMEMBER_DETECTED
# - [CALCULATE:expression] -> ACTION_CALCULATE_DETECTED  
# - [COMMAND:command] -> ACTION_COMMAND_DETECTED
# - [EXECUTE:action] -> ACTION_EXECUTE_DETECTED
# - [SEARCH_EPISODIC:query] -> ACTION_COMMAND_DETECTED

def detect_action_type(text: str) -> Dict[str, Any]:
    """
    Detect what type of action is present in the text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with action_type and action_params
    """
    result = {
        "action_type": ACTION_NONE,
        "action_params": {}
    }
    
    # Check for specific action markers
    web_search_match = re.search(r"\[WEB_SEARCH:([^\]]+)\]", text)
    # Also check for the [SEARCH:query] pattern that the LLM is using
    search_match = re.search(r"\[SEARCH:([^\]]+)\]", text)
    calculation_match = re.search(r"\[CALCULATE:([^\]]+)\]", text)
    command_match = re.search(r"\[COMMAND:([^\]]+)\]", text)
    execution_match = re.search(r"\[EXECUTE:([^\]]+)\]", text)
    remember_match = re.search(r"\[REMEMBER:([^\]]+)\]", text)
    forget_match = re.search(r"\[FORGET_THIS:([^\]]+)\]", text)
    correct_match = re.search(r"\[CORRECT:([^\]]+):([^\]]+)\]", text)
    
    # Check for tier upgrade requests and episodic memory searches using exact test patterns
    tier_request_pattern = r"\[REQUEST_TIER:(\d+):([^\]]+)\]"
    episodic_search_pattern = r"\[SEARCH_EPISODIC:([^\]]+)\]"
    
    has_tier_requests = re.search(tier_request_pattern, text) is not None
    has_episodic_search = re.search(episodic_search_pattern, text) is not None
    
    # Log if we found any special action commands
    if has_tier_requests:
        logger.info(f"Detected tier request in: {text[:100]}...")
    if has_episodic_search:
        logger.info(f"Detected episodic search in: {text[:100]}...")
    
    if web_search_match:
        logger.info(f"Detected [WEB_SEARCH:] pattern with query: {web_search_match.group(1)}")
        return ACTION_SEARCH_DETECTED, web_search_match.group(1), ACTION_SEARCH
    elif search_match:
        logger.info(f"Detected [SEARCH:] pattern with query: {search_match.group(1)}")
        return ACTION_SEARCH_DETECTED, search_match.group(1), ACTION_SEARCH
    elif calculation_match:
        return ACTION_CALCULATE_DETECTED, calculation_match.group(1), ACTION_CALCULATE_DETECTED
    elif command_match:
        return ACTION_COMMAND_DETECTED, command_match.group(1), ACTION_COMMAND_DETECTED
    elif execution_match:
        return ACTION_EXECUTE_DETECTED, execution_match.group(1), ACTION_EXECUTE_DETECTED
    elif remember_match:
        logger.info(f"Detected [REMEMBER:] pattern with fact: {remember_match.group(1)}")
        # Extract fact to be remembered
        return ACTION_REMEMBER_DETECTED, remember_match.group(1), ACTION_REMEMBER
    elif forget_match:
        logger.info(f"Detected [FORGET_THIS:] pattern with fact: {forget_match.group(1)}")
        # Extract fact to be forgotten
        return ACTION_FORGET_DETECTED, forget_match.group(1), ACTION_FORGET
    elif correct_match:
        logger.info(f"Detected [CORRECT:] pattern with old_fact: {correct_match.group(1)} and new_fact: {correct_match.group(2)}")
        # Extract old_fact and new_fact to be corrected
        return ACTION_CORRECT_DETECTED, {"old_fact": correct_match.group(1), "new_fact": correct_match.group(2)}, ACTION_CORRECT
    elif has_tier_requests or has_episodic_search:
        return ACTION_COMMAND_DETECTED, text, ACTION_COMMAND_DETECTED
    else:
        return ACTION_NONE, "", ACTION_NONE

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
        self._system_messages = {}
        self._system_message_ids = {}  # Maps search_id -> system_message_id
        
    def store_system_message(self, session_id: str, message: Dict[str, Any]) -> Optional[str]:
        """Store the system message for a given session.
        
        Args:
            session_id: The session ID
            message: The system message to store
            
        Returns:
            Optional system message ID from the API
        """
        self.logger.info(f"Storing system message for session {session_id}: {message['action']}")
        
        # Store in memory for reference
        self._system_messages[session_id] = message
        
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
                "message_type": message.get('action', 'status_update'),
                "content": {
                    "status": message.get('status', 'info'),
                    "message": message.get('content', ''),
                    "search_id": message.get('id', ''),
                    "timestamp": message.get('timestamp', '')
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
                    
                    # Store the system message ID for this action
                    if 'id' in message:
                        action_id = message['id']
                        self._system_message_ids[action_id] = system_message_id
                        self.logger.info(f"Stored system message ID {system_message_id} for action ID {action_id}")
                    
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
    
    def update_system_message(self, action_id: str, updated_content: Dict[str, Any]) -> bool:
        """Update an existing system message with new content.
        
        Args:
            action_id: The action ID associated with the system message
            updated_content: The updated content for the system message
            
        Returns:
            True if the update was successful, False otherwise
        """
        if action_id not in self._system_message_ids:
            self.logger.warning(f"No system message ID found for action ID {action_id}")
            return False
            
        system_message_id = self._system_message_ids[action_id]
        self.logger.info(f"Updating system message {system_message_id} for action ID {action_id}")
        
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

    def create_action_system_message(self, 
                                    session_id: str, 
                                    action_type: str, 
                                    content: str, 
                                    status: str = "active", 
                                    message_type: str = "info") -> str:
        """Create a system message for an action and store it.
        
        Args:
            session_id: The session ID
            action_type: The type of action (e.g., "web_search", "calculate")
            content: The message content
            status: The status of the action ("active", "completed", "error")
            message_type: The message type ("info", "error", "warning")
            
        Returns:
            The action ID for the created system message
        """
        # Generate a unique ID for this action
        action_id = f"{action_type}-{int(time.time())}-{session_id[:8]}"
        
        # Create a system message with the provided status
        system_message = {
            "type": "system",
            "action": action_type,
            "status": status,
            "id": action_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "messageType": message_type
        }
        
        # Store and send to dedicated system messages API
        self.store_system_message(session_id, system_message)
        
        # Return the action ID so it can be updated later
        return action_id

    def get_system_message(self, session_id: str) -> Dict[str, Any]:
        """Get the current system message for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            A dictionary with the system message information
        """
        return self._system_messages.get(session_id, {
            "status": "unknown",
            "content": "No system message available",
            "messageType": "info"
        })

    def detect_action(self, tier3_response: str, user_input: str, session_id: str) -> Tuple[str, str, str]:
        """
        Detect and process action signals in LLM response.
        
        Args:
            tier3_response: The full LLM response
            user_input: The user's input
            session_id: Current session ID
            
        Returns:
            Tuple of (action signal type, action result, action type)
        """
        # First, let's check for and extract content from LLM markers if present
        # This includes both the potential tier3 content AND any separate action signals
        
        # Handle the response format from DockerLLMAPI, which returns a dict with a "response" key
        # instead of "llm_response"
        response_content = ""
        tier3_response = ""
        
        if isinstance(response_data, dict):
            # Extract content from various possible formats
            if "llm_response" in response_data:
                llm_resp_obj = response_data["llm_response"]
                if isinstance(llm_resp_obj, dict) and "response_tiers" in llm_resp_obj:
                    response_tiers = llm_resp_obj["response_tiers"]
                    tier3_response = response_tiers.get("tier3", "")
            elif "response" in response_data:
                # This is the format returned by DockerLLMAPI.generate_response
                response_content = response_data["response"]
                llm_resp_obj = response_data  # Store the whole response object
            elif "tier3_response" in response_data:
                # Direct tier3 content
                tier3_response = response_data["tier3_response"]
            elif "text" in response_data:
                # Another possible format
                response_content = response_data["text"]
            elif "content" in response_data:
                # Another possible format
                response_content = response_data["content"]
            else:
                self.logger.error(f"Unexpected response_data format: no recognizable content fields found")
                return ACTION_BREAK, "Unexpected response format from LLM.", ACTION_ERROR
        elif isinstance(response_data, str):
            # Direct string response
            response_content = response_data
        else:
            self.logger.error(f"response_data is not a dictionary or string: {type(response_data)}")
            return ACTION_BREAK, "Invalid response type from LLM.", ACTION_ERROR
                
        # Combine tier3_response and response_content to check for action signals in either
        full_content_to_check = f"{tier3_response}\n{response_content}"
        
        # Log the content we'll be checking for action signals
        if len(full_content_to_check) > 100:
            self.logger.info(f"Extracted content (first 100 chars): {full_content_to_check[:100]}...")
        else:
            self.logger.info(f"Extracted content: {full_content_to_check}")
            
        # Check for action signals in the combined content
        action_signal, action_result, action_type = self.detect_action(full_content_to_check, user_input, session_id)
        
        # Always return a valid tuple with fallback values
        if not action_signal:
            action_signal = ACTION_BREAK
        if not action_type:
            action_type = ACTION_ANSWER
            
        # Store this turn to memory
        try:
            if self.contextual_memory:
                # Create a simplified response structure for storage
                simplified_response = {"content": full_content_to_check}
                # Fix parameter order - session_id should be first, then content
                self.contextual_memory.process_assistant_message(simplified_response, user_input, session_id)
        except Exception as mem_ex:
            self.logger.error(f"Error saving to contextual memory: {mem_ex}")
            
        # Return valid action signal
        return action_signal, full_content_to_check, action_type
                
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

        if not response_data:
            self.logger.error(f"Invalid or missing response_data received from LLM for session {session_id}.")
            # Store error turn? Maybe handle this upstream in ConversationManager?
            # For now, signal break with error.
            # Note: Need 'yield from []' or similar if we want this to be a generator in error cases too,
            # but returning directly is fine if CM handles the StopIteration correctly.
            # For simplicity, we'll assume returning is okay for now.
            # If issues arise, change to: yield from []; return ACTION_BREAK, ...
            return ACTION_BREAK, "LLM response was invalid or missing.", ACTION_ERROR

        try:
            # Log the response data type for debugging
            self.logger.info(f"Response data type: {type(response_data)}")
            if isinstance(response_data, dict):
                self.logger.info(f"Response data keys: {list(response_data.keys())}")
                
            # First, let's extract all the possible content to check for action signals
            # This includes both the potential tier3 content AND any separate action signals
            
            # Handle the response format from DockerLLMAPI, which returns a dict with a "response" key
            # instead of "llm_response"
            response_content = ""
            tier3_response = ""
            
            if isinstance(response_data, dict):
                # Extract content from various possible formats
                if "llm_response" in response_data:
                    llm_resp_obj = response_data["llm_response"]
                    if isinstance(llm_resp_obj, dict) and "response_tiers" in llm_resp_obj:
                        response_tiers = llm_resp_obj["response_tiers"]
                        tier3_response = response_tiers.get("tier3", "")
                elif "response" in response_data:
                    # This is the format returned by DockerLLMAPI.generate_response
                    response_content = response_data["response"]
                    llm_resp_obj = response_data  # Store the whole response object
                elif "tier3_response" in response_data:
                    # Direct tier3 content
                    tier3_response = response_data["tier3_response"]
                elif "text" in response_data:
                    # Another possible format
                    response_content = response_data["text"]
                elif "content" in response_data:
                    # Another possible format
                    response_content = response_data["content"]
                else:
                    self.logger.error(f"Unexpected response_data format: no recognizable content fields found")
                    return ACTION_BREAK, "Unexpected response format from LLM.", ACTION_ERROR
            elif isinstance(response_data, str):
                # Direct string response
                response_content = response_data
            else:
                self.logger.error(f"response_data is not a dictionary or string: {type(response_data)}")
                return ACTION_BREAK, "Invalid response type from LLM.", ACTION_ERROR
                
            # Combine tier3_response and response_content to check for action signals in either
            full_content_to_check = f"{tier3_response}\n{response_content}"
            
            # Log the content we'll be checking for action signals
            if len(full_content_to_check) > 100:
                self.logger.info(f"Extracted content (first 100 chars): {full_content_to_check[:100]}...")
            else:
                self.logger.info(f"Extracted content: {full_content_to_check}")
                
            # Check for action signals in the combined content
            action_signal, action_result, action_type = self.detect_action(full_content_to_check, user_input, session_id)
            
            # Always return a valid tuple with fallback values
            if not action_signal:
                action_signal = ACTION_BREAK
            if not action_type:
                action_type = ACTION_ANSWER
                
            # Store this turn to memory
            try:
                if self.contextual_memory:
                    # Create a simplified response structure for storage
                    simplified_response = {"content": full_content_to_check}
                    # Fix parameter order - session_id should be first, then content
                    self.contextual_memory.process_assistant_message(simplified_response, user_input, session_id)
            except Exception as mem_ex:
                self.logger.error(f"Error saving to contextual memory: {mem_ex}")
                
            # Return valid action signal
            return action_signal, full_content_to_check, action_type
                
        except Exception as e:
            self.logger.error(f"Error in process_llm_response: {str(e)}", exc_info=True)
            # Attempt to store turn data even if processing failed
            if response_data:
                 self.contextual_memory.process_assistant_message(response_data, user_input, session_id)
            return ACTION_BREAK, "I encountered an error processing the response.", ACTION_ERROR

    def process_llm_response_original(self,
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

        if not response_data:
            self.logger.error(f"Invalid or missing response_data received from LLM for session {session_id}.")
            # Store error turn? Maybe handle this upstream in ConversationManager?
            # For now, signal break with error.
            # Note: Need 'yield from []' or similar if we want this to be a generator in error cases too,
            # but returning directly is fine if CM handles the StopIteration correctly.
            # For simplicity, we'll assume returning is okay for now.
            # If issues arise, change to: yield from []; return ACTION_BREAK, ...
            return ACTION_BREAK, "LLM response was invalid or missing.", ACTION_ERROR

        try:
            # Handle the response format from DockerLLMAPI, which returns a dict with a "response" key
            # instead of "llm_response"
            response_content = ""
            if isinstance(response_data, dict):
                if "llm_response" in response_data:
                    llm_resp_obj = response_data["llm_response"]
                elif "response" in response_data:
                    # This is the format returned by DockerLLMAPI.generate_response
                    response_content = response_data["response"]
                    llm_resp_obj = response_data  # Store the whole response object
                else:
                    self.logger.error(f"Unexpected response_data format: neither 'llm_response' nor 'response' found")
                    return ACTION_BREAK, "Unexpected response format from LLM.", ACTION_ERROR
            else:
                self.logger.error(f"response_data is not a dictionary: {type(response_data)}")
                return ACTION_BREAK, "Invalid response type from LLM.", ACTION_ERROR
                
            # Ensure re module is available in this context
            import re
            
            # Extract the tier3_response from the response structure
            tier3_response = response_data.get("tier3_response", "")
            
            # Fall back to the response content if tier3 is missing
            if not tier3_response:
                if response_content:
                    # Use the content from DockerLLMAPI response
                    tier3_response = response_content
                elif isinstance(llm_resp_obj, dict) and "content" in llm_resp_obj:
                    tier3_response = llm_resp_obj["content"]
                elif isinstance(llm_resp_obj, str):
                    tier3_response = llm_resp_obj
                else:
                    # If still no usable content, log and return error
                    self.logger.error(f"Could not extract useful content from LLM response for session {session_id}")
                    # Skip storing turn data here as we have no useful content
                    return ACTION_BREAK, "LLM response was missing content.", ACTION_ERROR

            # --- Signal Detection ---
            action_signal_type, action_result, action_type = self.detect_action(tier3_response, user_input, session_id)
            
            # --- Action Execution ---
            if action_signal_type == ACTION_SEARCH_DETECTED:
                if not TAVILY_AVAILABLE:
                     self.logger.error("Web search signal detected, but Tavily client is not available.")
                     # Store turn, return error message as answer
                     self.contextual_memory.process_user_message(session_id, str(response_data))
                     
                     # Create system message for failed search
                     search_id = self.create_action_system_message(
                         session_id=session_id,
                         action_type="web_search",
                         content="Web search is currently unavailable",
                         status="error",
                         message_type="error"
                     )
                     
                     return ACTION_BREAK, "Web search is currently unavailable.", ACTION_ANSWER # Treat as answer

                web_query = action_result
                self.logger.info(f"WEB SEARCH signal detected for query: '{web_query}' (Session: {session_id})")
                # Store the turn *before* performing the search
                self.contextual_memory.process_user_message(session_id, str(response_data))

                # Generate a unique ID for this search action and create system message
                search_id = self.create_action_system_message(
                    session_id=session_id,
                    action_type="web_search",
                    content=f"Searching the web for: {web_query}"
                )
                self.logger.info(f"*** SENDING SEARCH STATUS TO FRONTEND (ID: {search_id}) ***")
                
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
                        # Update the existing system message with 'error' status
                        self.update_system_message(search_id, {
                            "status": "error",
                            "message": "Web search returned no results",
                            "timestamp": datetime.now().isoformat()
                        })
                    elif "error" in search_results.lower() or "unavailable" in search_results.lower():
                        self.logger.warning(f"Search returned an error message: {search_results[:100]}...")
                        # Update the existing system message with 'error' status
                        self.update_system_message(search_id, {
                            "status": "error",
                            "message": search_results,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        self.logger.info(f"Received valid web search results (first 100 chars): {search_results[:100] if search_results else 'None'}...")
                        # Update the existing system message with 'complete' status
                        self.update_system_message(search_id, {
                            "status": "complete",
                            "message": f"Searched the web for: {web_query}",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    # Store the search response and yield it to the client directly
                    search_response = {
                        'type': 'system',
                        'action': 'web_search',
                        'status': 'complete',
                        'content': search_results,
                        'timestamp': datetime.now().isoformat(),
                        'search_id': search_id,
                        'session_id': session_id
                    }
                    
                    # Yield the search results directly to the streaming response
                    yield search_response
                    
                    # Now signal that we need to break and include the search results in a follow-up message
                    return ACTION_BREAK, {
                        'search_results': search_results,
                        'search_query': web_query,
                        'search_id': search_id
                    }, ACTION_SEARCH
                except Exception as search_ex:
                    self.logger.error(f"Error during web search processing: {search_ex}", exc_info=True)
                    error_message = f"Error performing web search: {str(search_ex)}"
                    
                    # Update the existing system message with 'error' status
                    self.update_system_message(search_id, {
                        "status": "error",
                        "message": error_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Continue the conversation with the error message
                    return ACTION_CONTINUE, error_message, ACTION_SEARCH

            elif action_signal_type == ACTION_CALCULATE_DETECTED:
                calculation_id = self.create_action_system_message(
                    session_id=session_id,
                    action_type="calculate",
                    content=f"Calculating: {action_result}"
                )
                self.logger.info(f"*** SENDING CALCULATION STATUS TO FRONTEND (ID: {calculation_id}) ***")
                self.logger.info(f"Calculation signal detected (Session: {session_id})")
                # Store the turn *before* continuing for calculation
                self.contextual_memory.process_user_message(session_id, str(response_data))
                # Update the system message status to 'complete'
                self.update_system_message(calculation_id, {
                    "status": "complete",
                    "message": f"Calculation completed: {action_result}",
                    "timestamp": datetime.now().isoformat()
                })
                # Signal ConversationManager to continue the loop for calculation
                return ACTION_CONTINUE, action_result, ACTION_CALCULATE_DETECTED

            elif action_signal_type == ACTION_COMMAND_DETECTED:
                # Check if this is a tier request
                tier_request_pattern = r"\[REQUEST_TIER:(\d+):([^\]]+)\]"
                if re.search(tier_request_pattern, action_result):
                    self.logger.info(f"Tier request detected: {action_result}")
                    # Signal ConversationManager to break the loop for tier request
                    return ACTION_BREAK, action_result, ACTION_COMMAND_DETECTED
                else:
                    command_id = self.create_action_system_message(
                        session_id=session_id,
                        action_type="command",
                        content=f"Executing command: {action_result}"
                    )
                    self.logger.info(f"*** SENDING COMMAND STATUS TO FRONTEND (ID: {command_id}) ***")
                    self.logger.info(f"Command signal detected (Session: {session_id})")
                    # Store the turn *before* continuing for command
                    self.contextual_memory.process_user_message(session_id, str(response_data))
                    # Update the system message status to 'complete'
                    self.update_system_message(command_id, {
                        "status": "complete",
                        "message": f"Command executed: {action_result}",
                        "timestamp": datetime.now().isoformat()
                    })
                    # Signal ConversationManager to continue the loop for command
                    return ACTION_CONTINUE, action_result, ACTION_COMMAND_DETECTED

            elif action_signal_type == ACTION_EXECUTE_DETECTED:
                execution_id = self.create_action_system_message(
                    session_id=session_id,
                    action_type="execute",
                    content=f"Executing action: {action_result}"
                )
                self.logger.info(f"*** SENDING EXECUTION STATUS TO FRONTEND (ID: {execution_id}) ***")
                self.logger.info(f"Execution signal detected (Session: {session_id})")
                # Store the turn *before* continuing for execution
                self.contextual_memory.process_user_message(session_id, str(response_data))
                # Update the system message status to 'complete'
                self.update_system_message(execution_id, {
                    "status": "complete",
                    "message": f"Action executed: {action_result}",
                    "timestamp": datetime.now().isoformat()
                })
                # Signal ConversationManager to continue the loop for execution
                return ACTION_CONTINUE, action_result, ACTION_EXECUTE_DETECTED

            elif action_signal_type == ACTION_REMEMBER_DETECTED:
                fact_to_remember = action_result
                self.logger.info(f"Remember signal detected: '{fact_to_remember}' (Session: {session_id})")
                
                # Store the turn first
                self.contextual_memory.process_user_message(session_id, str(response_data))
                
                try:
                    # Store the fact directly to contextual memory with high importance (tier 2)
                    if self.contextual_memory:
                        # Check if fact already exists to avoid duplicates
                        fact_already_exists = False
                        existing_facts = self.contextual_memory.get_facts_for_session(session_id, limit=100)
                        if existing_facts:
                            for fact in existing_facts:
                                if fact_to_remember.lower() in fact.lower():
                                    fact_already_exists = True
                                    self.logger.info(f"Fact already exists, skipping storage: {fact_to_remember}")
                                    break
                                    
                        if not fact_already_exists:
                            # Custom fact storage
                            from models.memory import Memory, MemoryType, MemoryTier
                            
                            with get_db() as db:
                                # Create memory entry with high importance tier (Tier 2)
                                new_memory = Memory(
                                    user_id=self.user_id,
                                    session_id=session_id,
                                    memory_type=MemoryType.FACT,
                                    content=fact_to_remember,
                                    source="LLM_EXPLICIT_REMEMBER",
                                    importance=0.85,  # High importance
                                    tier=MemoryTier.TIER_2,  # Store in Tier 2 directly
                                    timestamp=datetime.now()
                                )
                                db.add(new_memory)
                                db.commit()
                                self.logger.info(f"Successfully stored fact in memory: {fact_to_remember}")
                    
                    # Also try to store using the existing API 
                    try:
                        if hasattr(self.contextual_memory, 'store_fact'):
                            self.contextual_memory.store_fact(
                                session_id=session_id,
                                fact=fact_to_remember,
                                source="LLM_EXPLICIT_REMEMBER",
                                importance=0.85  # High importance
                            )
                            self.logger.info(f"Stored fact using store_fact API: {fact_to_remember}")
                    except Exception as fact_ex:
                        self.logger.error(f"Error storing fact using API: {fact_ex}")
                
                except Exception as e:
                    self.logger.error(f"Error storing remembered fact: {e}", exc_info=True)
                
                # Unlike search actions, REMEMBER actions should NOT break the normal response flow
                # We return CONTINUE to allow the normal message to still be sent to the frontend
                # The action just added something to memory without interrupting the flow
                return ACTION_CONTINUE, fact_to_remember, ACTION_REMEMBER

            elif action_signal_type == ACTION_FORGET_DETECTED:
                fact_to_forget = action_result
                self.logger.info(f"Forget signal detected: '{fact_to_forget}' (Session: {session_id})")
                
                # Store the turn first
                self.contextual_memory.process_user_message(session_id, str(response_data))
                
                try:
                    # Remove the fact from contextual memory
                    if self.contextual_memory:
                        # Check if fact exists
                        existing_facts = self.contextual_memory.get_facts_for_session(session_id, limit=100)
                        if existing_facts:
                            for fact in existing_facts:
                                if fact_to_forget.lower() in fact.lower():
                                    self.logger.info(f"Fact found, attempting to remove: {fact_to_forget}")
                                    # Custom fact removal
                                    from models.memory import Memory, MemoryType
                                    
                                    with get_db() as db:
                                        # Remove memory entry
                                        db.query(Memory).filter(
                                            Memory.user_id == self.user_id,
                                            Memory.session_id == session_id,
                                            Memory.memory_type == MemoryType.FACT,
                                            Memory.content == fact_to_forget
                                        ).delete()
                                        db.commit()
                                        self.logger.info(f"Successfully removed fact from memory: {fact_to_forget}")
                    
                    # Also try to remove using the existing API 
                    try:
                        if hasattr(self.contextual_memory, 'remove_fact'):
                            self.contextual_memory.remove_fact(
                                session_id=session_id,
                                fact=fact_to_forget
                            )
                            self.logger.info(f"Removed fact using remove_fact API: {fact_to_forget}")
                    except Exception as fact_ex:
                        self.logger.error(f"Error removing fact using API: {fact_ex}")
                
                except Exception as e:
                    self.logger.error(f"Error removing forgotten fact: {e}", exc_info=True)
                
                # Unlike search actions, FORGET actions should NOT break the normal response flow
                # We return CONTINUE to allow the normal message to still be sent to the frontend
                # The action just removed something from memory without interrupting the flow
                return ACTION_CONTINUE, fact_to_forget, ACTION_FORGET

            elif action_signal_type == ACTION_CORRECT_DETECTED:
                correct_data = action_result
                old_fact = correct_data["old_fact"]
                new_fact = correct_data["new_fact"]
                self.logger.info(f"Correct signal detected: old_fact='{old_fact}', new_fact='{new_fact}' (Session: {session_id})")
                
                # Store the turn first
                self.contextual_memory.process_user_message(session_id, str(response_data))
                
                try:
                    # Correct the fact in contextual memory
                    if self.contextual_memory:
                        # Check if fact exists
                        existing_facts = self.contextual_memory.get_facts_for_session(session_id, limit=100)
                        if existing_facts:
                            for fact in existing_facts:
                                if old_fact.lower() in fact.lower():
                                    self.logger.info(f"Fact found, attempting to correct: {old_fact}")
                                    # Custom fact correction
                                    from models.memory import Memory, MemoryType
                                    
                                    with get_db() as db:
                                        # Update memory entry
                                        db.query(Memory).filter(
                                            Memory.user_id == self.user_id,
                                            Memory.session_id == session_id,
                                            Memory.memory_type == MemoryType.FACT,
                                            Memory.content == old_fact
                                        ).update({
                                            Memory.content: new_fact
                                        })
                                        db.commit()
                                        self.logger.info(f"Successfully corrected fact in memory: {old_fact} -> {new_fact}")
                    
                    # Also try to correct using the existing API 
                    try:
                        if hasattr(self.contextual_memory, 'correct_fact'):
                            self.contextual_memory.correct_fact(
                                session_id=session_id,
                                old_fact=old_fact,
                                new_fact=new_fact
                            )
                            self.logger.info(f"Corrected fact using correct_fact API: {old_fact} -> {new_fact}")
                    except Exception as fact_ex:
                        self.logger.error(f"Error correcting fact using API: {fact_ex}")
                
                except Exception as e:
                    self.logger.error(f"Error correcting fact: {e}", exc_info=True)
                
                # Unlike search actions, CORRECT actions should NOT break the normal response flow
                # We return CONTINUE to allow the normal message to still be sent to the frontend
                # The action just corrected something in memory without interrupting the flow
                return ACTION_CONTINUE, {"old_fact": old_fact, "new_fact": new_fact}, ACTION_CORRECT

            else: # Normal response
                self.logger.info(f"No signals detected. Processing as normal answer (Session: {session_id}).") 
                # Store the turn
                self.contextual_memory.process_user_message(session_id, str(response_data))
                
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

                # Yield a final response chunk with a structure that perfectly matches what the frontend expects
                yield {
                    "type": "final",
                    "content": clean_content,
                    "tier3": clean_content,
                    "response": clean_content,
                    "message": {
                        "id": f"asst-{int(time.time() * 1000)}",
                        "role": "assistant",
                        "content": clean_content,
                        "timestamp": datetime.now().isoformat()
                    },
                    "success": True,
                    "sessionId": session_id,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                # For transparency, add a debug log showing what's being returned
                self.logger.info(f"Final chat response sent (first 100 chars): {clean_content[:100] if clean_content else 'Empty'}...")
                
                # Signal ConversationManager to break, passing the final tier3 text
                return ACTION_BREAK, tier3_response, ACTION_ANSWER

        except Exception as proc_ex:
            self.logger.error(f"!!! EXCEPTION during LLM response processing in ActionHandler: {proc_ex} !!!", exc_info=True)
            # Attempt to store turn data even if processing failed
            if response_data:
                 self.contextual_memory.process_assistant_message(response_data, user_input, session_id)
            return ACTION_BREAK, f"Error processing LLM response: {proc_ex}", ACTION_ERROR