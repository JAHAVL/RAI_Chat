# RAI_Chat/backend/services/memory/contextual.py

import json
import os
import re
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# Import from the new structure
from .episodic import EpisodicMemoryManager
from llm_Engine.llm_api_bridge import get_llm_api # Or pass LLM API instance

# Import path utilities
from ...utils.path import LOGS_DIR, ensure_directory_exists, get_user_session_context_filepath, get_user_base_dir
# Import DB models and session type
from ...core.database.models import User
from sqlalchemy.orm import Session as SQLAlchemySession
logger_cmm = logging.getLogger(__name__) # Module-level logger

# Base path is now managed by path_manager.py

class ContextualMemoryManager:
    """
    Manages the active conversation window context for a specific session,
    and user-level persistent memory ('remember_this' facts).
    Handles storing turns, extracting memories, triggering archiving to episodic memory.
    """
    ACTIVE_TOKEN_LIMIT = 30000
    MIN_TOKENS_TO_PRUNE = 5000

    def __init__(self, user_id: int, episodic_memory_manager: EpisodicMemoryManager): # Removed base_data_path argument
        """Initialize the contextual memory manager for a specific user."""
        if not isinstance(user_id, int) or user_id <= 0:
             raise ValueError("Invalid user_id provided to ContextualMemoryManager.")
        self.user_id = user_id
        self.episodic_memory = episodic_memory_manager
        self.llm_api = get_llm_api()

        # User-specific logger setup (consider moving to a central logging config)
        self.logger = logging.getLogger(f"CtxMemMgr_User{self.user_id}")
        if not self.logger.hasHandlers(): # Avoid adding handlers multiple times
             self.logger.setLevel(logging.INFO)
             log_dir_path = LOGS_DIR # Use central logs dir for now
             try:
                 ensure_directory_exists(log_dir_path)
                 log_file_path = log_dir_path / f'contextual_memory_user_{self.user_id}.log'
                 handler = logging.FileHandler(log_file_path, encoding='utf-8')
                 formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                 handler.setFormatter(formatter)
                 self.logger.addHandler(handler)
             except Exception as e:
                 logger_cmm.error(f"CRITICAL: Failed to set up file logging for CtxMemMgr user {self.user_id}: {e}", exc_info=True)
                 # Continue without file logging for this instance if setup fails

        # Ensure base user data directory exists
        self._ensure_user_data_dirs_exist()

        # User-level memory is now stored in the database, removing file paths
        # self.user_memory_dir = get_user_memory_dir(self.user_id) # Removed
        # self.remember_this_file = self.user_memory_dir / "remember_this.json" # Removed

        # Initialize memory structures
        self.user_remembered_facts: List[str] = [] # User-level facts only
        self.active_session_id: Optional[str] = None
        self.active_session_context: Dict[str, Any] = self._get_empty_session_context() # Holds loaded session data

        # User-level data (facts) will be loaded on demand from DB when needed
        # self.load_user_remembered_facts() # Removed from init
        self.logger.info(f"ContextualMemoryManager initialized for user {self.user_id}.")

    # --- Path Helpers ---

    # Removed _get_user_memory_path and _get_user_sessions_path - use path_manager functions

    def _get_session_context_path(self, session_id: str) -> Path:
        """Gets the path to a specific session's context file using the new path manager function."""
        # Use the updated path manager function
        return get_user_session_context_filepath(self.user_id, session_id)

    def _ensure_user_data_dirs_exist(self) -> None:
        """Ensures the base user data directory and user-level memory directory exist."""
        try:
            user_base_path = get_user_base_dir(self.user_id)
            user_base_path.mkdir(parents=True, exist_ok=True)
            # Session directories (user_base_path / session_id) are created on demand when saving context/transcript
            self.logger.debug(f"Ensured user base directory exists: {user_base_path}")
        except OSError as e:
            self.logger.error(f"CRITICAL: Failed to create base data directories for user {self.user_id}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize base data directories for user {self.user_id}") from e

    # --- User-Level Memory Handling ---

    def load_user_remembered_facts(self, db: SQLAlchemySession) -> None:
        """Loads 'remember this' facts from the user's record in the database."""
        self.user_remembered_facts = [] # Start fresh
        try:
            user = db.query(User).filter(User.user_id == self.user_id).first()
            if user and user.remembered_facts:
                # Attempt to load JSON data; ensure it's a list
                loaded_facts = user.remembered_facts
                if isinstance(loaded_facts, list):
                    self.user_remembered_facts = loaded_facts
                    self.logger.info(f"Loaded {len(self.user_remembered_facts)} facts from DB for user {self.user_id}")
                else:
                    self.logger.warning(f"Invalid format for remembered_facts in DB for user {self.user_id}, expected a list. Resetting facts.")
            elif user:
                 self.logger.info(f"No remembered facts found in DB for user {self.user_id}.")
            else:
                 self.logger.error(f"User {self.user_id} not found in DB during fact loading.")

        except Exception as e:
            self.logger.error(f"Error loading user facts from DB for user {self.user_id}: {e}", exc_info=True)
            self.user_remembered_facts = [] # Reset on error

    def save_user_remembered_facts(self, db: SQLAlchemySession) -> None:
        """Saves the current 'remember this' facts to the user's record in the database."""
        try:
            # Find the user record
            user = db.query(User).filter(User.user_id == self.user_id).first()
            if user:
                # Update the remembered_facts field
                user.remembered_facts = self.user_remembered_facts
                # db.add(user) # Not needed if user is already tracked by session
                # Commit will happen outside this function, typically by the caller managing the session scope
                self.logger.info(f"Updated remembered_facts in DB for user {self.user_id} ({len(self.user_remembered_facts)} facts). Pending commit.")
            else:
                 self.logger.error(f"User {self.user_id} not found in DB. Cannot save facts.")

        except Exception as e:
            self.logger.error(f"Error saving user facts to DB for user {self.user_id}: {e}", exc_info=True)

    def process_forget_command(self, db: SQLAlchemySession, user_input: str) -> bool:
        """
        Detects and processes explicit user commands to forget specific facts.
        Removes the fact from this user's remembered facts and saves the update to the DB.
        Requires a DB session.
        """
        processed = False
        input_lower = user_input.lower()
        forget_patterns = [r"forget (?:that )?(.*)", r"don't remember (?:that )?(.*)", r"remove (.*?) from (?:your|the) memory"]
        fact_to_forget = None

        for pattern in forget_patterns:
            match = re.search(pattern, input_lower)
            if match:
                fact_to_forget = match.group(1).strip().rstrip('.?!')
                fact_to_forget = re.sub(r"^(my|i|i'm|i am)\s+", "User ", fact_to_forget, flags=re.IGNORECASE)
                fact_to_forget = re.sub(r"\s+(is|are|was|were)\s+", " ", fact_to_forget) # Simplify verb
                break

        if fact_to_forget:
            self.logger.info(f"Detected potential forget command for fact: '{fact_to_forget}'")
            initial_fact_count = len(self.user_remembered_facts)
            facts_to_keep = [f for f in self.user_remembered_facts if fact_to_forget not in f.lower()]

            if len(facts_to_keep) < initial_fact_count:
                self.user_remembered_facts = facts_to_keep
                self.save_user_remembered_facts(db) # Save the updated facts to DB
                self.logger.info(f"Removed {initial_fact_count - len(facts_to_keep)} fact(s) related to '{fact_to_forget}'.")
                processed = True
            else:
                self.logger.info(f"No stored facts matched '{fact_to_forget}' to forget.")
                processed = True # Command understood but no matching fact found

        return processed

    def get_remember_this_content(self) -> str:
        """Formats the user's remembered facts into a string."""
        if not self.user_remembered_facts:
            return "User has not asked to remember anything specific yet."
        else:
            formatted_facts = "\n".join([f"- {fact}" for fact in self.user_remembered_facts])
            return f"Facts the user wants you to remember:\n{formatted_facts}"

    # --- Session Context Handling ---

    def _get_empty_session_context(self) -> Dict[str, Any]:
        """Returns the structure for an empty session context."""
        return {
            "messages": [], # List of turn objects
            "current_context_summary": "" # Store only the latest summary/state needed for next prompt
            # Add other session-specific state if needed, e.g., metadata extracted from turns
        }

    def load_session_context(self, session_id: str) -> bool:
        """
        Loads the context for the specified session_id into memory.
        Sets self.active_session_id and self.active_session_context.

        Returns:
            True if loaded successfully (or initialized new), False on error.
        """
        if self.active_session_id == session_id:
            self.logger.debug(f"Session {session_id} context already active.")
            return True # Already loaded

        context_path = self._get_session_context_path(session_id)
        self.logger.info(f"Loading session context for {session_id} from {context_path}")

        if context_path.is_file():
            try:
                with open(context_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                # Basic validation
                if isinstance(loaded_data, dict) and "messages" in loaded_data:
                    self.active_session_context = loaded_data
                    self.active_session_id = session_id
                    self.logger.info(f"Successfully loaded context for session {session_id} ({len(loaded_data.get('messages',[]))} messages).")
                    return True
                else:
                    self.logger.warning(f"Invalid format in {context_path}. Initializing empty context.")
                    self.active_session_context = self._get_empty_session_context()
                    self.active_session_id = session_id
                    return True # Treat as new session initialization
            except (IOError, json.JSONDecodeError) as e:
                self.logger.error(f"Error loading session context from {context_path}: {e}", exc_info=True)
                # Don't set active session if load fails critically
                # self.active_session_context = self._get_empty_session_context()
                # self.active_session_id = None # Indicate failure
                return False
        else:
            self.logger.info(f"Context file {context_path} not found. Initializing empty context for new session {session_id}.")
            self.active_session_context = self._get_empty_session_context()
            self.active_session_id = session_id
            return True # New session initialized

    def save_session_context(self) -> bool:
        """Saves the currently active session context to its file."""
        if not self.active_session_id:
            self.logger.error("Cannot save session context: No active session ID.")
            return False

        context_path = self._get_session_context_path(self.active_session_id)
        self.logger.info(f"Saving active session context for {self.active_session_id} to {context_path}")

        try:
            # Ensure directory exists
            context_path.parent.mkdir(parents=True, exist_ok=True)
            with open(context_path, 'w', encoding='utf-8') as f:
                json.dump(self.active_session_context, f, indent=4)
            self.logger.info(f"Successfully saved context for session {self.active_session_id}")
            return True
        except (IOError, TypeError) as e:
            self.logger.error(f"Error saving session context to {context_path}: {e}", exc_info=True)
            return False
        except Exception as e:
             self.logger.error(f"Unexpected error saving session context to {context_path}: {e}", exc_info=True)
             return False

    def reset_session_context(self, session_id: str) -> bool:
        """
        Resets the context for a session: clears in-memory state (if active)
        and deletes the context file.
        """
        self.logger.warning(f"Attempting to reset context for session: {session_id}")
        file_deleted = False
        memory_cleared = False

        # Clear in-memory context if it's the active one
        if self.active_session_id == session_id:
            self.active_session_context = self._get_empty_session_context()
            self.active_session_id = None # No longer active after reset
            memory_cleared = True
            self.logger.info(f"Cleared active in-memory context for session {session_id}.")

        # Delete the context file
        context_path = self._get_session_context_path(session_id)
        try:
            if context_path.is_file():
                context_path.unlink()
                file_deleted = True
                self.logger.info(f"Deleted session context file: {context_path}")
            else:
                self.logger.info(f"Session context file not found, nothing to delete: {context_path}")
                file_deleted = True # Consider successful if file doesn't exist

        except OSError as e:
            self.logger.error(f"Error deleting session context file {context_path}: {e}", exc_info=True)
            file_deleted = False # Mark as failed
        except Exception as e:
             self.logger.error(f"Unexpected error deleting context file {context_path}: {e}", exc_info=True)
             file_deleted = False

        # TODO: Consider if associated episodic memory for the session also needs clearing
        # This might involve calling a method on self.episodic_memory

        return file_deleted # Return True if file deletion was successful (or file didn't exist)

    # --- Core Turn Processing ---

    def process_user_message(self, session_id: str, user_input: str) -> None:
        """
        Handles user input. Currently just logs it, as the turn object is created
        when the assistant response is processed. Ensures the session context is loaded.
        """
        if not self.load_session_context(session_id):
             # Handle error - perhaps raise exception or return error status
             self.logger.error(f"Failed to load or initialize context for session {session_id}. Cannot process user message.")
             raise RuntimeError(f"Failed to load context for session {session_id}")

        # No longer returns message_id, just ensures context is ready
        self.logger.info(f"Processing user input for active session {self.active_session_id}: {user_input[:100]}...")

    def process_assistant_message(self, response_data: Dict[str, Any], user_input: str) -> bool:
        """
        Processes the LLM's response for the **active session**, stores the complete turn,
        extracts memories, triggers archiving, and saves the updated context.

        Args:
            response_data: The complex JSON object returned by the LLM.
            user_input: The original raw user input string for this turn.

        Returns:
            True if processing and saving were successful, False otherwise.
        """
        if not self.active_session_id or not self.active_session_context:
            self.logger.error("Cannot process assistant message: No active session context loaded.")
            return False

        session_id = self.active_session_id # Use the active session ID
        turn_id = self._generate_message_id()

        # --- 1. Store Turn Data ---
        turn_object = {
            "turn_id": turn_id,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "llm_output": response_data # Store the full response object
        }
        # Ensure 'messages' list exists before appending
        if "messages" not in self.active_session_context:
             self.active_session_context["messages"] = []
        self.active_session_context["messages"].append(turn_object)
        self.logger.info(f"Stored turn {turn_id} for active session {session_id}")

        # --- 1b. Update Current Context Summary ---
        # Store a concise summary/state needed for the *next* prompt generation
        # This might be tier1 or tier2 from the LLM response, or a custom summary.
        # For now, let's store the LLM's Tier 2 summary if available.
        current_summary = ""
        if response_data and isinstance(response_data, dict):
             try:
                  llm_t2 = response_data.get("llm_response", {}).get("response_tiers", {}).get("tier2", "")
                  self.active_session_context["current_context_summary"] = llm_t2
                  self.logger.info(f"Updated current_context_summary for session {session_id}: '{llm_t2[:50]}...'")
             except Exception as ctx_ex:
                  self.logger.error(f"Error updating current_context_summary: {ctx_ex}", exc_info=True)
        else:
             self.logger.warning("Cannot update current_context_summary, response_data is invalid.")
             self.active_session_context["current_context_summary"] = "" # Clear if invalid


        # --- 2. Memory Extraction (operates on self.user_remembered_facts) ---
        if response_data and isinstance(response_data, dict):
            # (Memory extraction logic remains largely the same, but uses self.user_remembered_facts)
            MEMORY_EXTRACTION_PROMPT = """Analyze the following User message and Assistant response. Identify any potential facts, preferences, or key information about the user that should be remembered for future interactions. Output ONLY a JSON list of strings. If no relevant information is found, output an empty list []. Example: ["User's dog is named Max.", "User prefers short summaries."] Potential facts/preferences:"""
            try:
                llm_response_t3 = response_data.get("llm_response", {}).get("response_tiers", {}).get("tier3", "")
                if self.llm_api and llm_response_t3:
                    extraction_prompt_text = MEMORY_EXTRACTION_PROMPT + f"\n\nUser Message:\n{user_input}\n\nAssistant Response:\n{llm_response_t3}\n\nPotential facts/preferences:\n"
                    messages = [{"role": "user", "content": extraction_prompt_text}]
                    self.logger.debug("Sending request to LLM API for memory extraction")
                    extraction_response = self.llm_api.chat_completion(messages=messages, temperature=0.2, max_tokens=512)
                    if extraction_response and "content" in extraction_response:
                        generated_text = extraction_response["content"].strip()
                        try:
                            # Basic cleanup for potential markdown code blocks
                            if generated_text.startswith("```json"): generated_text = generated_text[7:]
                            if generated_text.endswith("```"): generated_text = generated_text[:-3]
                            suggested_memories = json.loads(generated_text)
                            if isinstance(suggested_memories, list) and suggested_memories:
                                self.logger.info(f"Suggested memory items: {suggested_memories}")
                                current_facts = set(self.user_remembered_facts)
                                new_facts = [fact for fact in suggested_memories if fact not in current_facts]
                                if new_facts:
                                    self.user_remembered_facts.extend(new_facts)
                                    self.logger.info(f"Added {len(new_facts)} new facts to user memory (will be saved with session context or explicitly).")
                                    # Removed automatic save here - facts are saved with session context or via forget command
                                    # self.save_user_remembered_facts(db) # Requires db session passed down
                        except json.JSONDecodeError:
                            self.logger.warning(f"Memory extraction response was not valid JSON: {generated_text}")
                        except Exception as e:
                             self.logger.error(f"Error processing memory extraction result: {e}", exc_info=True)
                else:
                     self.logger.warning("Skipping memory extraction (no LLM API or T3 response).")
            except Exception as e:
                self.logger.error(f"Error during memory extraction LLM call: {e}", exc_info=True)
        else:
             self.logger.warning("Skipping memory extraction as LLM response data is invalid.")


        # --- 3. Archiving Trigger & Logic (Token-Based) ---
        try:
            messages = self.active_session_context.get("messages", []) # Use .get for safety
            if not messages: # Skip if no messages
                 self.logger.debug("No messages in active context, skipping archiving check.")
            else:
                total_token_count = sum(self._estimate_turn_tokens(turn) for turn in messages)
                self.logger.info(f"Session {session_id}: Active history token count ~{total_token_count} / {self.ACTIVE_TOKEN_LIMIT}")

                if total_token_count > self.ACTIVE_TOKEN_LIMIT:
                    self.logger.warning(f"--- PRUNING TRIGGERED --- Token limit ({self.ACTIVE_TOKEN_LIMIT}) exceeded (~{total_token_count} tokens).")
                    tokens_to_prune = total_token_count - self.ACTIVE_TOKEN_LIMIT + self.MIN_TOKENS_TO_PRUNE
                    self.logger.info(f"Targeting prune of at least {tokens_to_prune} tokens.")

                    prune_index = 0
                    pruned_tokens = 0
                    for i, turn in enumerate(messages):
                        pruned_tokens += self._estimate_turn_tokens(turn)
                        prune_index = i + 1
                        if pruned_tokens >= tokens_to_prune:
                            break

                    if prune_index > 0:
                        chunk_to_archive = messages[:prune_index]
                        self.logger.info(f"Identified {prune_index} oldest turns (~{pruned_tokens} tokens) to archive.")
                        first_msg_ts = chunk_to_archive[0].get("timestamp", datetime.now().isoformat())
                        chunk_id = f"chunk_{first_msg_ts.replace(':','-').replace('.','-')}"

                        if hasattr(self, 'episodic_memory') and self.episodic_memory:
                            success = self.episodic_memory.archive_and_summarize_chunk(
                                session_id=session_id, # Pass session_id for context
                                chunk_id=chunk_id,
                                raw_chunk_data=chunk_to_archive,
                                user_id=self.user_id # Pass user_id
                            )

                            if success:
                                self.active_session_context["messages"] = messages[prune_index:]
                                self.logger.info(f"Successfully archived chunk {chunk_id} and pruned active history for session {session_id}. New count: {len(self.active_session_context['messages'])} turns.")
                            else:
                                self.logger.error(f"Failed to archive chunk {chunk_id} for session {session_id}. Active history not pruned.")
                        else:
                             self.logger.error("EpisodicMemoryManager instance not available. Cannot archive.")
                    else:
                         self.logger.warning("Token limit exceeded, but failed to identify chunk to prune.")
        except Exception as e:
            self.logger.error(f"Error during archiving process: {e}", exc_info=True)

        # --- 4. Save Updated Session Context ---
        save_successful = self.save_session_context()

        return save_successful # Return True if save was successful

    # --- Context Retrieval ---

    def get_context_summary(self) -> str:
        """Gets the current context summary for the active session."""
        if not self.active_session_id:
            self.logger.warning("Cannot get context summary: No active session.")
            return ""
        # Use .get for safety, default to empty string
        return self.active_session_context.get("current_context_summary", "")

    def get_formatted_history(self, limit: int = 20) -> str:
        """
        Retrieves recent conversation history for the active session and formats it.
        """
        if not self.active_session_id:
            self.logger.warning("Cannot get formatted history: No active session.")
            return "No active session."

        messages = self.active_session_context.get("messages", [])
        recent_turns = messages[-limit:] if limit > 0 else messages
        history_parts = []
        for turn in recent_turns:
            user_input = turn.get("user_input", "[User input missing]")
            llm_output_data = turn.get("llm_output")
            assistant_response = "[Assistant response missing or invalid]"
            if llm_output_data and isinstance(llm_output_data, dict):
                 # Display Tier 3 (full response) in history for clarity
                 assistant_response = llm_output_data.get("llm_response", {}).get("response_tiers", {}).get("tier3", "[Response content missing]")

            history_parts.append(f"User: {user_input}")
            history_parts.append(f"Assistant: {assistant_response}")

        return "\n".join(history_parts) if history_parts else "Conversation history is empty."

    # --- Helper Methods ---

    def _estimate_turn_tokens(self, turn_object: Dict[str, Any]) -> int:
        """Roughly estimates tokens in a turn object by character count."""
        # This is a very basic estimation. A proper tokenizer (like tiktoken) would be more accurate.
        # Factor of 4 is a common heuristic (chars to tokens).
        chars = 0
        if turn_object.get("user_input"):
            chars += len(turn_object["user_input"])
        llm_output = turn_object.get("llm_output")
        if llm_output and isinstance(llm_output, dict):
            # Estimate based on Tier 3 content if available
            t3_content = llm_output.get("llm_response", {}).get("response_tiers", {}).get("tier3", "")
            chars += len(t3_content)
            # Add chars for other structure if significant? For now, focus on main content.
        return chars // 4 # Rough estimate

    def _generate_message_id(self) -> str:
        """Generates a unique ID for a message or turn."""
        return str(uuid.uuid4())

    # --- Potentially Keep or Adapt ---
    # These might be useful depending on how episodic memory/working memory are used

    def get_episodic_memories(self, query: str) -> List[Dict]:
        """Retrieves relevant memories from the episodic store for the current user."""
        if hasattr(self, 'episodic_memory') and self.episodic_memory:
            # Pass user_id if the episodic manager needs it
            return self.episodic_memory.retrieve_memories(query=query, user_id=self.user_id)
        else:
            self.logger.warning("Episodic memory manager not available.")
            return []

    def get_working_memory(self) -> List[Dict]:
         """
         Placeholder: Retrieves items currently considered 'working memory'
         (e.g., recent episodic recalls, important facts for the current task).
         This might involve interaction with episodic memory or other state.
         """
         # For now, return empty or combine remembered facts + recent episodic?
         self.logger.warning("get_working_memory is not fully implemented.")
         # Example: return [{"type": "fact", "content": fact} for fact in self.user_remembered_facts]
         return []

    def inject_recalled_chunk(self, raw_chunk_data: List[Dict]) -> bool:
        """
        Injects turns from a recalled episodic chunk into the *beginning*
        of the active session's message history.
        """
        if not self.active_session_id:
            self.logger.error("Cannot inject recalled chunk: No active session.")
            return False
        if not isinstance(raw_chunk_data, list):
             self.logger.error("Cannot inject recalled chunk: Invalid chunk data format (must be list).")
             return False

        self.logger.info(f"Injecting {len(raw_chunk_data)} recalled turns into active session {self.active_session_id}")
        # Prepend the recalled turns to the current messages
        current_messages = self.active_session_context.get("messages", [])
        # Ensure 'messages' list exists before assigning
        if "messages" not in self.active_session_context:
             self.active_session_context["messages"] = []
        self.active_session_context["messages"] = raw_chunk_data + current_messages
        # Note: This might push the context over the token limit immediately.
        # Consider if pruning should happen after injection.
        # For now, let the regular pruning handle it on the *next* assistant message.
        return True # Return success, assuming save will happen later
