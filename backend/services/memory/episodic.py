# RAI_Chat/backend/services/memory/episodic.py

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
import glob
import hashlib
import time # Needed for LLM retry logic
from pathlib import Path

# Assuming the API bridge is accessible
from llm_Engine.llm_api_bridge import get_llm_api

# Import path utilities
from ...utils.path import ensure_directory_exists, LOGS_DIR, DATA_DIR

logger_emm = logging.getLogger(__name__) # Module-level logger

# Base path is now managed by path_manager.py

# Prompt specifically for summarizing a chunk of conversation for episodic memory
SUMMARIZE_CHUNK_PROMPT = """
Below is a chunk of conversation consisting of multiple exchanges. Each exchange includes a user prompt analysis and the LLM's response. Please provide a concise summary (3-5 sentences) covering the main topics, key decisions, important facts mentioned, and the overall sentiment or outcome of this conversation chunk. Focus on information that might be useful to recall later.

Conversation Chunk (User Prompt Tier 3 and LLM Response Tier 3 shown):
{conversation_chunk_text}

Summary:
"""

class EpisodicMemoryManager:
    """
    Manages episodic memory (long-term archive) for a specific user.
    Handles storing chunks of conversation, summarizing them using an LLM,
    and searching summaries to retrieve relevant past context for that user.
    """

    def __init__(self, user_id: int): # Removed base_data_path argument
        """Initialize the episodic memory manager for a specific user."""
        if not isinstance(user_id, int) or user_id <= 0:
             raise ValueError("Invalid user_id provided to EpisodicMemoryManager.")
        self.user_id = user_id

        # User-specific logger setup (consider moving to a central logging config)
        self.logger = logging.getLogger(f"EpisodicMemMgr_User{self.user_id}")
        if not self.logger.hasHandlers(): # Avoid adding handlers multiple times
            self.logger.setLevel(logging.INFO)
            log_dir_path = LOGS_DIR # Use central logs dir for now
            try:
                ensure_directory_exists(log_dir_path)
                log_file_path = log_dir_path / f'episodic_memory_user_{self.user_id}.log'
                handler = logging.FileHandler(log_file_path, encoding='utf-8')
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
            except Exception as e:
                logger_emm.error(f"CRITICAL: Failed to set up file logging for EpisodicMemMgr user {self.user_id}: {e}", exc_info=True)

        # Define user-specific episodic memory directory and paths using path_manager
        # self.user_memory_dir = get_user_memory_dir(self.user_id) # Removed usage of get_user_memory_dir
        self.episodic_dir = DATA_DIR / str(self.user_id) / "episodic" # Episodic dir directly under user's data dir
        self.archive_dir = self.episodic_dir / "archive" # Archive within episodic
        self.summary_index_file = self.episodic_dir / "summary_index.json" # Index within episodic

        # Ensure directories exist using helper
        try:
            # ensure_directory_exists(self.user_memory_dir) # Base memory dir created by ContextualMemoryManager usually
            ensure_directory_exists(self.episodic_dir) # Ensure episodic dir exists
            ensure_directory_exists(self.archive_dir) # Ensure archive subdir exists
        except (OSError, ValueError) as e:
             self.logger.error(f"CRITICAL: Failed to create episodic/archive directories for user {self.user_id}: {e}", exc_info=True)
             raise RuntimeError(f"Failed to initialize episodic/archive directories for user {self.user_id}") from e

        # Initialize LLM API
        self.llm_api = get_llm_api()
        if not self.llm_api:
             self.logger.error("Failed to initialize LLM API for EpisodicMemoryManager.")

        # Load summary index for this user
        self._load_summary_index()

        self.logger.info(f"EpisodicMemoryManager initialized for user {self.user_id}. Episodic path: {self.episodic_dir}")

    # --- Helper methods for index (operate on user-specific file) ---
    def _load_summary_index(self):
        """Loads the summary index file for this user."""
        try:
            # Use Path object's exists() method
            if self.summary_index_file.exists():
                with open(self.summary_index_file, 'r', encoding='utf-8') as f:
                    self.summary_index = json.load(f)
                self.logger.info(f"Loaded summary index for user {self.user_id} with {len(self.summary_index)} sessions from {self.summary_index_file}.")
            else:
                self.summary_index = {} # { session_id: { chunk_id: summary } }
                self.logger.info(f"Summary index file not found for user {self.user_id}. Initialized empty index.")
        except Exception as e:
            self.logger.error(f"Failed to load summary index for user {self.user_id}: {e}", exc_info=True)
            self.summary_index = {}

    def _save_summary_index(self):
        """Saves the summary index file for this user."""
        try:
            # Ensure user-specific episodic directory exists before saving index
            ensure_directory_exists(self.episodic_dir) # Use helper
            with open(self.summary_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.summary_index, f, indent=2)
            self.logger.debug(f"Saved summary index for user {self.user_id} to {self.summary_index_file}")
        except Exception as e:
            self.logger.error(f"Failed to save summary index for user {self.user_id}: {e}", exc_info=True)
    # --- End Helper methods ---

    def archive_and_summarize_chunk(self, session_id: str, chunk_id: str, raw_chunk_data: List[Dict], user_id: Optional[int] = None) -> bool:
        """
        Archives raw conversation data, calls LLM to summarize it, and stores the summary for the specific user.
        """
        if user_id is not None and user_id != self.user_id:
             self.logger.error(f"Mismatched user_id provided ({user_id}) to instance for user {self.user_id}.")
             return False

        if not self.llm_api:
            self.logger.error(f"LLM API not available for user {self.user_id}, cannot summarize chunk for archiving.")
            return False

        # 1. Save Raw Data (to user-specific episodic archive)
        try:
            # Ensure user-specific archive directory exists (already done in __init__, but safe to repeat)
            ensure_directory_exists(self.archive_dir) # Use helper
            # Construct archive file path using Path object (self.archive_dir is already correct)
            archive_file_path = self.archive_dir / f"{session_id}_{chunk_id}.json"
            with open(archive_file_path, 'w', encoding='utf-8') as f:
                json.dump(raw_chunk_data, f, indent=2)
            self.logger.info(f"Saved raw chunk {chunk_id} for session {session_id} (User: {self.user_id}) to {archive_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save raw chunk {chunk_id} for session {session_id} (User: {self.user_id}): {e}", exc_info=True)
            return False

        # 2. Prepare Text for Summarization (No changes needed here)
        conversation_chunk_text = ""
        summary = "No text content found in chunk."
        try:
            chunk_text_parts = []
            for turn in raw_chunk_data:
                 user_prompt = turn.get("user_input", "")
                 llm_output = turn.get("llm_output", {})
                 llm_response_t3 = llm_output.get("llm_response", {}).get("response_tiers", {}).get("tier3", "")
                 if user_prompt: chunk_text_parts.append(f"User: {user_prompt}")
                 if llm_response_t3: chunk_text_parts.append(f"Assistant: {llm_response_t3}")
            conversation_chunk_text = "\n".join(chunk_text_parts)
            if not conversation_chunk_text:
                 self.logger.warning(f"No text content found in chunk {chunk_id} (User: {self.user_id}) for summarization.")
        except Exception as e:
             self.logger.error(f"Error preparing chunk text for summarization (User: {self.user_id}): {e}", exc_info=True)
             summary = "Error preparing chunk text."

        # 3. Call LLM for Summarization (if text available) (No changes needed here)
        if conversation_chunk_text:
            try:
                summarization_prompt = SUMMARIZE_CHUNK_PROMPT.format(conversation_chunk_text=conversation_chunk_text)
                messages = [{"role": "user", "content": summarization_prompt}]
                self.logger.debug(f"Sending request to LLM API for chunk summarization (User: {self.user_id}, chunk {chunk_id})")
                # Add retry logic for LLM calls
                max_retries = 3
                retry_delay = 2 # seconds
                for attempt in range(max_retries):
                    try:
                        response = self.llm_api.chat_completion(messages=messages, temperature=0.5, max_tokens=256)
                        if response and "role" in response and "content" in response:
                            summary = response["content"].strip()
                            self.logger.info(f"Generated summary for chunk {chunk_id} (User: {self.user_id}): {summary[:100]}...")
                            break # Success, exit retry loop
                        else:
                            self.logger.error(f"Invalid response format from LLM during summarization (Attempt {attempt+1}/{max_retries}) for chunk {chunk_id} (User: {self.user_id}).")
                            summary = "Failed to generate summary (invalid format)."
                            if attempt == max_retries - 1: break # Don't sleep on last attempt
                            time.sleep(retry_delay)
                    except Exception as llm_e:
                         self.logger.error(f"Error during LLM call for summarization (Attempt {attempt+1}/{max_retries}) (User: {self.user_id}, chunk {chunk_id}): {llm_e}", exc_info=(attempt == max_retries - 1)) # Log full trace on last attempt
                         summary = f"Error during summarization: {llm_e}"
                         if attempt == max_retries - 1: break # Don't sleep on last attempt
                         time.sleep(retry_delay)
            except Exception as e: # Catch errors outside the retry loop
                self.logger.error(f"Unexpected error setting up LLM call for summarization (User: {self.user_id}, chunk {chunk_id}): {e}", exc_info=True)
                summary = f"Error setting up summarization: {e}"

        # 4. Store Summary in User's Index (No changes needed here)
        try:
            if session_id not in self.summary_index:
                self.summary_index[session_id] = {}
            self.summary_index[session_id][str(chunk_id)] = summary
            self._save_summary_index() # Saves the user-specific index
            self.logger.info(f"Stored summary for chunk {chunk_id} in index for user {self.user_id}.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to store summary for chunk {chunk_id} in index for user {self.user_id}: {e}", exc_info=True)
            return False

    def retrieve_memories(self, query: str, top_k: int = 5, user_id: Optional[int] = None) -> List[Dict]:
        """
        Searches all summaries across all sessions for the user and returns the top_k most relevant.
        (Changed from search_episodic_memory to reflect broader search)
        """
        if user_id is not None and user_id != self.user_id:
             self.logger.error(f"Mismatched user_id provided ({user_id}) to instance for user {self.user_id}.")
             return []

        self.logger.info(f"Searching all episodic summaries for user {self.user_id}, query: '{query}'")
        query_lower = query.lower()
        all_scored_summaries = []

        # Iterate through all sessions in the user's index
        for session_id, chunks in self.summary_index.items():
            for chunk_id, summary in chunks.items():
                score = self._calculate_summary_relevance(query_lower, summary.lower())
                if score > 0.1: # Basic threshold to filter out completely irrelevant summaries
                    all_scored_summaries.append({
                        "score": score,
                        "session_id": session_id,
                        "chunk_id": chunk_id,
                        "summary": summary
                    })

        if not all_scored_summaries:
            self.logger.info(f"No relevant summaries found across all sessions for user {self.user_id}.")
            return []

        # Sort all found summaries by score
        all_scored_summaries.sort(key=lambda x: x["score"], reverse=True)

        # Return the top_k results
        top_results = all_scored_summaries[:top_k]
        self.logger.info(f"Found {len(top_results)} relevant summaries (top {top_k}) for user {self.user_id}.")
        return top_results
        
    def search_episodic_memory(self, query: str, session_id: str = None, top_k: int = 5, search_depth: int = 0) -> str:
        """
        Compatibility method for older code that expects search_episodic_memory.
        Searches episodic memory and returns a formatted string of summaries.
        
        Args:
            query: The search query
            session_id: Optional session ID (not used in this implementation)
            top_k: Maximum number of results to return
            search_depth: Optional search depth (not used in this implementation)
            
        Returns:
            A formatted string of summaries
        """
        self.logger.info(f"search_episodic_memory called with query: '{query}', session_id: {session_id}, top_k: {top_k}, search_depth: {search_depth}")
        
        # Call retrieve_memories to get the actual results
        memories = self.retrieve_memories(query, top_k)
        
        # Format the results as a string
        if not memories:
            return ""
            
        formatted_summaries = "\n".join([f"- {memory['summary']}" for memory in memories])
        return formatted_summaries


    def _calculate_summary_relevance(self, query: str, summary: str) -> float:
        """Calculates a simple relevance score based on keyword overlap."""
        # (Implementation remains the same)
        query_words = set(re.findall(r'\w+', query)) # Extract words
        summary_words = set(re.findall(r'\w+', summary))
        if not query_words: return 0.0 # Avoid division by zero if query is empty
        common_words = query_words.intersection(summary_words)
        # Jaccard index variation - prioritize query coverage
        score = len(common_words) / len(query_words) if query_words else 0.0
        return score


    def get_raw_chunk(self, session_id: str, chunk_id: str) -> Optional[List[Dict]]:
        """
        Retrieves the raw chunk data for a given session and chunk ID for this user.
        """
        self.logger.info(f"Retrieving raw chunk {chunk_id} for session {session_id} (User: {self.user_id})")
        try:
            # Construct the user-specific archive file path using Path object
            # self.archive_dir is already correct
            archive_file_path = self.archive_dir / f"{session_id}_{chunk_id}.json"
            if archive_file_path.is_file(): # Use Path.is_file() for check
                with open(archive_file_path, 'r', encoding='utf-8') as f:
                    raw_chunk_data = json.load(f)
                self.logger.info(f"Successfully retrieved raw chunk {chunk_id} for user {self.user_id} from {archive_file_path}")
                return raw_chunk_data
            else:
                self.logger.warning(f"Raw chunk file not found for user {self.user_id}: {archive_file_path}")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving raw chunk {chunk_id} for user {self.user_id}: {e}", exc_info=True)
            return None

    def reset_session_in_memory(self, session_id: str) -> bool:
        """
        Resets the in-memory summary index for a specific session for this user.
        Does NOT delete archived chunk files.
        """
        if session_id in self.summary_index:
            self.logger.info(f"Resetting in-memory summary index for session: {session_id} (User: {self.user_id})")
            del self.summary_index[session_id]
            # self._save_summary_index() # Optionally save immediately
            return True
        else:
            self.logger.warning(f"Session {session_id} not found in summary index for user {self.user_id}. Cannot reset.")
            return False

    def delete_session_archive(self, session_id: str) -> bool:
        """
        Deletes all archived chunk files and the session's entry from the summary index
        for the specified session_id and user.
        """
        self.logger.warning(f"Attempting to delete ALL archived data for session {session_id} (User: {self.user_id})")
        session_found_in_index = session_id in self.summary_index
        files_deleted_count = 0
        errors = []

        # 1. Delete files from archive directory
        try:
            session_archive_pattern = self.archive_dir / f"{session_id}_*.json"
            # Use glob with Path object
            for file_path in self.archive_dir.glob(f"{session_id}_*.json"):
                try:
                    file_path.unlink()
                    files_deleted_count += 1
                    self.logger.info(f"Deleted archive file: {file_path}")
                except OSError as e:
                    self.logger.error(f"Error deleting archive file {file_path}: {e}")
                    errors.append(str(e))
        except Exception as e:
            self.logger.error(f"Error globbing/accessing archive directory {self.archive_dir} for deletion: {e}", exc_info=True)
            errors.append(str(e))

        # 2. Remove session from index and save
        if session_found_in_index:
            try:
                del self.summary_index[session_id]
                self._save_summary_index()
                self.logger.info(f"Removed session {session_id} from summary index.")
            except Exception as e:
                self.logger.error(f"Error removing session {session_id} from summary index: {e}", exc_info=True)
                errors.append(str(e))
        elif files_deleted_count > 0:
             self.logger.warning(f"Deleted {files_deleted_count} archive files for session {session_id}, but session was not found in index.")
        else:
             self.logger.info(f"No archive files or index entry found for session {session_id} to delete.")


        if errors:
             self.logger.error(f"Encountered {len(errors)} errors during deletion of session {session_id} archive.")
             return False
        else:
             self.logger.info(f"Successfully deleted archive data for session {session_id} (Files deleted: {files_deleted_count}, Index updated: {session_found_in_index}).")
             return True


    # --- Commented out potentially outdated/broken methods ---
    # (Keep commented out as before)
    # def _check_temporal_query(self, query: str) -> dict: ...
    # def _handle_temporal_query(self, query: str, temporal_info: dict, current_session_id: str) -> str: ...
    # def _summarize_conversation(self, messages: List[Dict[str, Any]]) -> str: ...
    # def _define_search_topics(self, query: str) -> Dict[str, float]: ...
    # def _search_stored_conversations(self, search_topics: Dict[str, float], current_session_id: str) -> List[Dict]: ...
    # def _extract_relevant_exchanges(self, messages: List[Dict[str, Any]], search_topics: Dict[str, float]) -> str: ...
    # def _calculate_relevance(self, user_content: str, topic: str) -> float: ...
    # def _format_search_results(self, relevant_exchanges: List[Dict], search_topics: Dict[str, float]) -> str: ...
    # def add_memory(self, user_message: str, assistant_message: str, timestamp=None): ...
    # def _create_new_memory_file(self, filename, memory_entry): ...
    # def _extract_search_topics(self, query: str) -> Dict[str, float]: ...
