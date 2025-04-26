# RAI_Chat/backend/services/conversation.py
import json
import os
import re
import requests # Keep for potential future use
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, TYPE_CHECKING, Generator # Added Generator
from sqlalchemy.orm import Session as SQLAlchemySession # For type hinting DB session

# Import type hints for managers using new paths
if TYPE_CHECKING:
    from ..managers.memory.contextual_memory import ContextualMemoryManager
    from ..managers.memory.episodic_memory import EpisodicMemoryManager
    from ..managers.user_session_manager import UserSessionManager

# Import concrete classes for runtime checks if needed
from .memory.contextual import ContextualMemoryManager
from .memory.episodic import EpisodicMemoryManager
from .file_storage import ChatFileManager

# Import database utilities
from models.connection import get_db

# Import from utils
from ..utils.pathconfig import LOGS_DIR, ensure_directory_exists

# Import components
from ..components.prompt_builder import PromptBuilder
from ..components.action_handler import ActionHandler, ACTION_CONTINUE, ACTION_BREAK, ACTION_FETCH, ACTION_SEARCH, ACTION_SEARCH_DEEPER, ACTION_ANSWER, ACTION_ERROR

# Import database models
from models.session import Session as SessionModel
from sqlalchemy import desc

import time
import sys
import traceback

# Import the LLM API from the new external location
from llm_Engine.llm_api_bridge import get_llm_api, get_llm_engine

logger = logging.getLogger(__name__) # Use module-level logger

class ConversationManager:
    """
    Orchestrates conversation flow, interacting with memory, LLM, and components.
    Uses pre-initialized, user-scoped managers.
    Manages the currently active chat session for a user.
    """

    def __init__(self,
                 user_id: int, # Explicitly require user_id
                 contextual_memory_manager: 'ContextualMemoryManager',
                 episodic_memory_manager: 'EpisodicMemoryManager',
                 chat_file_manager: 'ChatFileManager'):
        """
        Initialize conversation manager with pre-initialized, user-scoped managers
        and instantiate helper components. Does not load a session initially.

        Args:
            user_id: The ID of the user this manager instance belongs to.
            contextual_memory_manager: An initialized instance for the current user.
            episodic_memory_manager: An initialized instance for the current user.
            chat_file_manager: An initialized instance for the current user.
        """
        # Ensure managers are valid instances
        if not isinstance(contextual_memory_manager, ContextualMemoryManager):
             raise TypeError("Invalid ContextualMemoryManager instance provided.")
        if not isinstance(episodic_memory_manager, EpisodicMemoryManager):
             raise TypeError("Invalid EpisodicMemoryManager instance provided.")
        if not isinstance(chat_file_manager, ChatFileManager):
             raise TypeError("Invalid ChatFileManager instance provided.")
        if not isinstance(user_id, int) or user_id <= 0:
             raise ValueError("Invalid user_id provided.")

        self.user_id = user_id
        self.logger = logging.getLogger(f"ConvMgr_User{self.user_id}") # Instance logger

        # --- Logging Setup ---
        if not self.logger.hasHandlers():
            log_dir_path = LOGS_DIR
            try:
                ensure_directory_exists(log_dir_path)
                log_file_path = log_dir_path / f'conversation_user_{self.user_id}.log'
                handler = logging.FileHandler(log_file_path, encoding='utf-8')
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
            except Exception as e:
                 logger.error(f"CRITICAL: Failed to set up file logging for ConvMgr user {self.user_id}: {e}", exc_info=True)
        # --- End Logging Setup ---

        # Assign injected, user-scoped managers
        self.contextual_memory = contextual_memory_manager
        self.episodic_memory = episodic_memory_manager
        self.chat_file_manager = chat_file_manager

        # Instantiate helper components
        # TODO: Update PromptBuilder/ActionHandler if their init changes
        self.prompt_builder = PromptBuilder(self.contextual_memory, self.episodic_memory)
        self.action_handler = ActionHandler(self.contextual_memory, self.episodic_memory)

        # Initialize other components
        # self.calendar_manager = CalendarManager() # Removed - Module does not exist

        # Current session ID - Initialized to None. Must be set by load_chat or start_new_chat.
        self.current_session_id: Optional[str] = None
        self.logger.info(f"ConversationManager initialized for User ID: {self.user_id}. No session loaded initially.")

        # Track last message times (less critical now, context manager handles state)
        self.last_user_message = None
        self.last_response_time = None
        self.last_assistant_message = None

        # Initialize LLM API access
        self.llm_api = get_llm_api()
        # Legacy engine access (consider removing)
        self.llm_engine = get_llm_engine()


    def get_response(self, db: SQLAlchemySession, user_input: str) -> Generator[Dict[str, Any], None, None]:
        """
        Yields status updates and the final response from the AI model for the
        **currently active session**. Orchestrates prompt building, LLM calls,
        and action handling. Requires a session to be loaded first via
        load_chat or start_new_chat. Requires a database session.

        Yields:
            Dict[str, Any]: Status updates (e.g., {"status": "searching"}) or the final response object.
        """
        if not self.current_session_id:
             self.logger.error("Cannot get response: No active session loaded. Call load_chat or start_new_chat first.")
             # Return an error structure consistent with normal responses
             yield { # Yield error structure
                 "llm_response": {
                     "response_tiers": {
                         "tier1": "Error", "tier2": "No chat session is active.", "tier3": "No chat session is active."
                     }
                 },
                 "status": "error" # Add status for clarity
             }
             return # Stop the generator

        self.logger.info(f"Processing user input for active session {self.current_session_id}: {user_input[:100]}...")

        # --- Initial Checks & Commands ---
        if user_input.lower().strip() == "clear memory":
             self.logger.info(f"Processing 'clear memory' command for session {self.current_session_id}")
             # Reset context file and memory state
             self.contextual_memory.reset_session_context(self.current_session_id)
             # Reset episodic index for this session
             self.episodic_memory.reset_session_in_memory(self.current_session_id)
             # Note: This doesn't delete the DB record or transcript file, use delete_current_chat for that.
             yield {"llm_response": {"response_tiers": {"tier3": "Current chat session memory context has been cleared."}}, "status": "success"}
             return # Stop the generator

        # Forget command handled by ContextualMemoryManager now
        if self.contextual_memory.process_forget_command(db, user_input): # Pass db session
             self.logger.info("Processed a forget command.")
             yield {"llm_response": {"response_tiers": {"tier3": "Okay, I'll try to forget that."}}, "status": "success"}
             return # Stop the generator

        # Ensure ContextualMemoryManager knows about the user input for the active session
        self.contextual_memory.process_user_message(self.current_session_id, user_input)

        # --- Main Processing Loop ---
        search_depth = 0
        max_search_depth = 3
        processed_response_text = None
        final_response_data = None
        current_search_results = None
        last_search_results = None
        action_type = None
        chunk_id_to_fetch = None

        while search_depth < max_search_depth:
            try:
                self.logger.info(f"--- Starting response generation cycle (Session: {self.current_session_id}, Depth: {search_depth}) ---")

                # 1. Build Prompt (Uses active session context via ContextualMemoryManager)
                system_prompt = self.prompt_builder.construct_prompt(
                    session_id=self.current_session_id, # Pass session ID if needed by builder
                    user_input=user_input,
                    search_depth=search_depth,
                    web_search_results=current_search_results
                )
                current_search_results = None # Consume search results

                # 2. Call LLM
                response_data = self._generate_llm_response(system_prompt, user_input)

                # 3. Process Response & Handle Actions (Uses active session context)
                # 3. Process Response & Handle Actions (ActionHandler is now a generator)
                action_processor = self.action_handler.process_llm_response(
                    session_id=self.current_session_id,
                    user_input=user_input,
                    response_data=response_data
                )
                loop_signal, action_result, action_type = None, None, None # Initialize
                try:
                    while True: # Loop to get yielded values from ActionHandler
                        status_update = next(action_processor)
                        yield status_update # Yield status upwards to the API route
                except StopIteration as e:
                    # Generator finished, capture its return value
                    loop_signal, action_result, action_type = e.value
                    self.logger.info(f"ActionHandler returned: signal={loop_signal}, type={action_type}")

                # Ensure we captured the return value
                if loop_signal is None:
                     self.logger.error("ActionHandler finished without returning expected values!")
                     # Handle this error case, maybe yield an error and break
                     yield {"status": "error", "llm_response": {"response_tiers": {"tier3": "Internal error processing action."}}}
                     return # Stop generator


                # 4. Update Loop State based on ActionHandler result
                # (Logic remains similar, assuming ActionHandler uses active context)
                if loop_signal == ACTION_CONTINUE:
                    if action_type == ACTION_SEARCH:
                        current_search_results = action_result
                        last_search_results = action_result
                        self.logger.info("Continuing loop after web search.")
                        continue
                    elif action_type == ACTION_SEARCH_DEEPER:
                        search_depth += 1
                        self.logger.info(f"Continuing loop for deeper search (Depth: {search_depth}).")
                        continue
                    else:
                        self.logger.error(f"Unexpected ACTION_CONTINUE signal type: {action_type}")
                        break
                elif loop_signal == ACTION_BREAK:
                    if action_type == ACTION_ANSWER:
                        processed_response_text = action_result
                        self.logger.info("ActionHandler indicated ANSWER. Breaking loop.")
                    elif action_type == ACTION_FETCH:
                        self.logger.info("ActionHandler indicated FETCH. Breaking loop.")
                        chunk_id_to_fetch = action_result
                    elif action_type == ACTION_ERROR:
                        processed_response_text = action_result
                        self.logger.error(f"ActionHandler indicated ERROR: {action_result}. Breaking loop.")
                    else:
                        self.logger.error(f"Unexpected ACTION_BREAK signal type: {action_type}")
                    break
                else:
                    self.logger.error(f"Unknown loop signal from ActionHandler: {loop_signal}")
                    break

            except Exception as e:
                self.logger.error(f"Error during response generation cycle (Depth: {search_depth}): {e}", exc_info=True)
                processed_response_text = f"I encountered an error trying to generate a response (Depth: {search_depth})."
                action_type = ACTION_ERROR
                # Store minimal error turn data in the active context
                error_response_data = { "llm_response": {"response_tiers": {"tier1": processed_response_text, "tier2": processed_response_text, "tier3": processed_response_text}}}
                self.contextual_memory.process_assistant_message(error_response_data, user_input) # Save error turn
                break # Exit loop on cycle error

        # --- Post-Loop Processing ---

        # Handle Fetching & Rerun (if needed)
        if action_type == ACTION_FETCH and chunk_id_to_fetch:
            self.logger.info(f"Handling fetch request for chunk: {chunk_id_to_fetch}")
            try:
                # Use current_session_id when calling episodic memory
                raw_chunk_data = self.episodic_memory.get_raw_chunk(self.current_session_id, chunk_id_to_fetch)
                if raw_chunk_data:
                    # Use contextual memory's method for injection
                    injection_success = self.contextual_memory.inject_recalled_chunk(raw_chunk_data)
                    if injection_success:
                        self.logger.info(f"Successfully injected chunk {chunk_id_to_fetch}. Re-running get_response.")
                        # Recursive call - yield results from it
                        yield from self.get_response(db, user_input) # Pass db session
                        return # Stop this generator branch
                    else:
                        self.logger.error(f"Failed to inject chunk {chunk_id_to_fetch}. Aborting fetch rerun.")
                        processed_response_text = "I found some relevant information but had trouble processing it."
                        action_type = ACTION_ERROR
                else:
                    self.logger.error(f"Failed to retrieve raw chunk {chunk_id_to_fetch}. Aborting fetch rerun.")
                    processed_response_text = "I tried to recall specific details, but couldn't retrieve them."
                    action_type = ACTION_ERROR
            except Exception as fetch_ex:
                 self.logger.error(f"Error during chunk fetch/injection process: {fetch_ex}", exc_info=True)
                 processed_response_text = "An error occurred while trying to recall specific details."
                 action_type = ACTION_ERROR

        # --- Prepare Final Response ---
        # (Logic remains similar, constructs final_response_data based on action_type)
        if action_type == ACTION_ANSWER:
            final_answer_text = self._post_process_response(processed_response_text or "")
            final_response_data = { "llm_response": { "response_tiers": { "tier1": final_answer_text[:50] + "...", "tier2": final_answer_text[:150] + "...", "tier3": final_answer_text } } }
            self.logger.info("Final response prepared (ACTION_ANSWER).")
        elif action_type == ACTION_ERROR:
            final_response_data = { "llm_response": { "response_tiers": { "tier1": "Error", "tier2": processed_response_text or "An unknown error occurred.", "tier3": processed_response_text or "An unknown error occurred." } } }
            self.logger.info("Final response prepared (ACTION_ERROR).")
        else: # Fallback if loop finished unexpectedly
             self.logger.warning(f"Loop finished without definitive action (Last type: {action_type}). Using fallback response.")
             fallback_text = processed_response_text or "I'm sorry, I encountered an issue and couldn't provide a response."
             final_response_data = { "llm_response": { "response_tiers": { "tier1": "Processing Issue", "tier2": fallback_text, "tier3": fallback_text } } }

        # --- Safeguard against returning raw [SEARCH:] command ---
        # (Logic remains similar)
        try:
            final_tier3 = final_response_data.get("llm_response", {}).get("response_tiers", {}).get("tier3", "")
            if "[SEARCH:" in final_tier3:
                self.logger.warning("LLM returned [SEARCH:] command unexpectedly. Replacing with fallback message.")
                if last_search_results:
                     fallback_msg = f"I performed a web search but couldn't synthesize a direct answer. Here are the raw results I found:\n\n{last_search_results}"
                     fallback_tier1 = "Search completed, showing raw results."
                else:
                     fallback_msg = "I attempted a web search, but encountered an issue and couldn't retrieve results or synthesize an answer."
                     fallback_tier1 = "Search attempted, but failed."
                final_response_data["llm_response"]["response_tiers"]["tier1"] = fallback_tier1
                final_response_data["llm_response"]["response_tiers"]["tier2"] = fallback_msg
                final_response_data["llm_response"]["response_tiers"]["tier3"] = fallback_msg
        except Exception as safeguard_ex:
             self.logger.error(f"Error during [SEARCH:] safeguard check: {safeguard_ex}")


        # --- Final Step: Save the turn data via ContextualMemoryManager ---
        # This now happens inside the loop via ActionHandler calling process_assistant_message,
        # or during error handling. If the loop completes without error/answer,
        # we might need an explicit save here if process_assistant_message wasn't called.
        # However, the current logic ensures process_assistant_message is called within ActionHandler
        # before breaking with ACTION_ANSWER. Let's assume saving is handled.
        # If not, add: self.contextual_memory.process_assistant_message(final_response_data, user_input)

        self.logger.info("Returning final structured response data.")
        self.logger.debug(f"--- DEBUG: ConversationManager returning value (type: {type(final_response_data)}): {str(final_response_data)[:200]}... ---")
        # Yield the final prepared response data
        yield final_response_data
        return # End the generator


    def load_chat(self, session_id: str) -> bool:
        """
        Loads a specific chat session context into memory.

        Args:
            session_id: The ID of the session to load.

        Returns:
            True if the session context was loaded successfully, False otherwise.
        """
        self.logger.info(f"Attempting to load chat session: {session_id}")
        try:
            # Delegate loading to ContextualMemoryManager
            success = self.contextual_memory.load_session_context(session_id)
            if success:
                self.current_session_id = session_id # Update active session ID
                self.logger.info(f"Successfully loaded and set active session: {session_id}")
                return True
            else:
                self.logger.error(f"Failed to load context for session {session_id}.")
                self.current_session_id = None # Ensure no session is active if load fails
                return False
        except Exception as e:
            self.logger.error(f"Error loading chat session {session_id}: {e}", exc_info=True)
            self.current_session_id = None
            return False

    def save_current_chat(self, db: SQLAlchemySession): # Requires DB session
        """
        Saves the currently active chat session's context and transcript,
        and updates/creates the session metadata in the database.
        """
        if not self.current_session_id:
             self.logger.warning("No current session active to save.")
             return False

        self.logger.info(f"Saving current chat session: {self.current_session_id}")
        try:
            # 1. Save the context file (.json with messages, summary etc.)
            context_save_success = self.contextual_memory.save_session_context()
            if not context_save_success:
                 self.logger.error(f"Failed to save session context file for {self.current_session_id}.")
                 # Continue to try and save transcript/metadata? Or return False? Let's return False.
                 return False

            # 2. Prepare transcript data (just the messages) and metadata
            messages = self.contextual_memory.active_session_context.get("messages", [])
            # Generate title (example - could be improved)
            title = "Untitled Chat"
            for turn in messages:
                 if turn.get("user_input"):
                      title = turn["user_input"][:30] + "..." if len(turn["user_input"]) > 30 else turn["user_input"]
                      break
            metadata = {"title": title} # Add other metadata if needed

            # 3. Save transcript file and DB metadata via ChatFileManager
            transcript_save_success = self.chat_file_manager.save_session_transcript(
                db=db,
                user_id=self.user_id,
                session_id=self.current_session_id,
                transcript_data=messages, # Save full turn objects as transcript for now
                session_metadata=metadata
            )

            if not transcript_save_success:
                 self.logger.error(f"Failed to save session transcript/metadata for {self.current_session_id}.")
                 # Context was saved, but transcript/DB failed - log inconsistency
                 return False

            self.logger.info(f"Successfully saved session {self.current_session_id} (context, transcript, metadata).")
            return True

        except Exception as e:
            self.logger.error(f"Error saving current chat {self.current_session_id}: {e}", exc_info=True)
            return False


    def list_saved_sessions(self, db: SQLAlchemySession) -> List[Dict[str, Any]]: # Requires DB session
        """Lists saved chat sessions using the ChatFileManager (which queries DB)."""
        try:
            return self.chat_file_manager.list_sessions(db=db, user_id=self.user_id)
        except Exception as e:
            self.logger.error(f"Error listing saved sessions: {e}", exc_info=True)
            return []

    def get_saved_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Gets saved message history (transcript) for a session using ChatFileManager."""
        try:
            # Assuming transcript file contains the desired history format (e.g., list of turns)
            return self.chat_file_manager.get_session_transcript(user_id=self.user_id, session_id=session_id)
        except Exception as e:
            self.logger.error(f"Error getting saved session history for {session_id}: {e}", exc_info=True)
            return None

    def _generate_llm_response(self, system_prompt: str, user_input: str) -> Optional[Dict[str, Any]]:
        """Generates response from LLM API, handling retries and simple response parsing."""
        # (Implementation remains largely the same, ensure logging uses self.logger)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        self.logger.info(f"Prepared {len(messages)} messages for LLM API (System + User Input)")

        # Log the prompt being sent to the LLM
        try:
            prompt_log_dir = LOGS_DIR / 'Conversation_Manager_Prompts'
            ensure_directory_exists(prompt_log_dir)
            timestamp_log = datetime.now().strftime("%Y%m%d_%I%M%S%p")
            # Use current_session_id in log filename
            log_file_path = prompt_log_dir / f"PROMPT_User{self.user_id}_{self.current_session_id or 'NOSESSION'}_{timestamp_log}.log"
            with open(log_file_path, 'w', encoding='utf-8') as f:
                 f.write(f"--- System Prompt ---\n{system_prompt}\n\n--- User Input ---\n{user_input}\n")
            self.logger.info(f"Conversation Manager prompt logged to: {log_file_path}")
        except Exception as log_e:
            self.logger.error(f"Failed to log Conversation Manager prompt: {log_e}")

        max_retries = 3
        retry_delay = 2 # seconds
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Sending request to LLM API (Attempt {attempt + 1})")
                response_data = self.llm_api.chat_completion(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                    session_id=self.current_session_id # Pass active session ID
                )
                # (Rest of parsing/error handling logic as before)
                if response_data and isinstance(response_data, dict):
                     self.logger.info(f"Raw response from LLM API: {str(response_data)[:200]}...")
                     if "llm_response" in response_data and "response_tiers" in response_data["llm_response"]:
                          return response_data
                     elif "role" in response_data and "content" in response_data:
                          self.logger.warning("LLM response was simple role/content. Attempting to parse 'content' as structured JSON.")
                          raw_content_string = response_data.get("content", "").strip()
                          cleaned_content_str = re.sub(r'^```json\s*|\s*```$', '', raw_content_string, flags=re.MULTILINE).strip()
                          try:
                              parsed_content = json.loads(cleaned_content_str)
                              self.logger.info("Successfully parsed 'content' string as JSON.")
                              if isinstance(parsed_content, dict) and "llm_response" in parsed_content and "response_tiers" in parsed_content["llm_response"]:
                                   self.logger.info("Parsed content has expected structure. Returning parsed dictionary.")
                                   return parsed_content
                              else:
                                   self.logger.error("Parsed 'content' string does not have the expected structure.")
                                   error_structure = {"user_message_analysis": {"prompt_tiers": {"tier1": "Analysis N/A", "tier2": "Analysis N/A"}}, "llm_response": {"response_tiers": {"tier1": raw_content_string, "tier2": raw_content_string, "tier3": raw_content_string}}}
                                   return error_structure
                          except json.JSONDecodeError as json_err:
                              self.logger.error(f"Failed to parse 'content' string as JSON: {json_err}. Content was: '{cleaned_content_str}'")
                              error_structure = {"user_message_analysis": {"prompt_tiers": {"tier1": "Analysis N/A", "tier2": "Analysis N/A"}}, "llm_response": {"response_tiers": {"tier1": raw_content_string, "tier2": raw_content_string, "tier3": raw_content_string}}}
                              return error_structure
                     else:
                          self.logger.error(f"LLM response dictionary has unexpected structure: {response_data}")
                          return None
                elif response_data == "[NEED_MORE_CONTEXT]":
                     self.logger.warning("LLM signaled [NEED_MORE_CONTEXT].")
                     return response_data # Propagate signal
                else:
                     self.logger.error(f"LLM API returned invalid data type or None: {type(response_data)}")

            except requests.exceptions.RequestException as req_err:
                self.logger.error(f"Network error connecting to LLM API (Attempt {attempt + 1}): {req_err}")
            except Exception as e:
                self.logger.error(f"Error during LLM API call (Attempt {attempt + 1}): {e}", exc_info=True)

            if attempt < max_retries - 1:
                self.logger.info(f"Retrying LLM API call in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                self.logger.error("LLM API call failed after multiple retries.")
                return None # Failed after retries
        return None # Should not be reached if loop completes normally


    def start_new_chat(self) -> str:
        """
        Starts a new chat session by generating a new session ID and loading
        an empty context for it.
        """
        new_session_id = str(uuid.uuid4())
        self.logger.info(f"Starting new chat session: {new_session_id}")
        # Load context will initialize empty if file doesn't exist
        load_success = self.contextual_memory.load_session_context(new_session_id)
        if load_success:
            self.current_session_id = new_session_id
            self.logger.info(f"New session {new_session_id} started and set as active.")
            return new_session_id
        else:
            # This indicates a problem creating the context file/directory potentially
            self.logger.error(f"Failed to initialize context for new session {new_session_id}.")
            raise RuntimeError(f"Could not start new chat session {new_session_id}")


    def set_current_session(self, session_id: str) -> bool:
        """Sets the current active session ID after loading its context."""
        return self.load_chat(session_id)


    def delete_current_chat(self, db: SQLAlchemySession): # Requires DB session
        """
        Deletes the currently active chat session (context file, transcript file, DB record).
        """
        if not self.current_session_id:
             self.logger.warning("No current session selected to delete.")
             return False

        session_id_to_delete = self.current_session_id
        self.logger.warning(f"Attempting to delete current chat session: {session_id_to_delete}")

        # 1. Delete context file and clear from memory
        context_deleted = self.contextual_memory.reset_session_context(session_id_to_delete)
        if not context_deleted:
             self.logger.error(f"Failed to delete context file for session {session_id_to_delete}. Aborting full delete.")
             # Should we still try to delete DB/transcript? Maybe log inconsistency.
             return False

        # 2. Delete transcript file and DB record via ChatFileManager
        db_transcript_deleted = self.chat_file_manager.delete_session(db, self.user_id, session_id_to_delete)
        if not db_transcript_deleted:
             self.logger.error(f"Failed to delete transcript file and/or DB record for session {session_id_to_delete}.")
             # Context file was deleted, but this failed. Log inconsistency.
             return False

        # 3. Delete episodic memory index entry for the session
        self.episodic_memory.reset_session_in_memory(session_id_to_delete)
        # Optionally delete archived episodic files too?
        # self.episodic_memory.delete_session_archive(session_id_to_delete)

        self.logger.info(f"Successfully deleted session {session_id_to_delete}.")
        self.current_session_id = None # Clear active session ID
        # Optionally load the last active session or start a new one?
        # self.get_last_active_session(db) # Requires db session
        return True


    def get_current_messages(self) -> List[Dict]:
        """Gets the messages (turn objects) for the currently active session."""
        if not self.current_session_id:
            self.logger.warning("Cannot get messages: No active session.")
            return []
        # Messages are stored within the active context
        return self.contextual_memory.active_session_context.get("messages", [])

    def get_last_active_session(self, db: SQLAlchemySession) -> Optional[str]: # Requires DB session
        """Gets the ID of the most recently active session from the database."""
        self.logger.info("Attempting to get the last active session ID from DB.")
        try:
            latest_session = db.query(SessionModel.session_id).filter(
                SessionModel.user_id == self.user_id
            ).order_by(
                desc(SessionModel.last_activity_at)
            ).first()

            if latest_session:
                session_id = latest_session.session_id
                self.logger.info(f"Found last active session: {session_id}")
                # Optionally load it immediately?
                # self.load_chat(session_id)
                return session_id
            else:
                self.logger.info("No previous sessions found for this user.")
                return None
        except Exception as e:
            self.logger.error(f"Error getting last active session from DB: {e}", exc_info=True)
            return None


    def _post_process_response(self, response: str) -> str:
        """Basic post-processing for the final response text."""
        # (Implementation remains the same)
        # Remove potential leading/trailing whitespace
        processed = response.strip()
        # Add other cleanup rules if needed
        return processed
