# RAI_Chat/Backend/managers/user_session_manager.py

import logging
import time
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

# Import the manager classes we need to instantiate
from managers.chat_file_manager import ChatFileManager
from managers.memory.contextual_memory import ContextualMemoryManager
from managers.memory.episodic_memory import EpisodicMemoryManager
from managers.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

# Define a base path for data storage - In a real app, load this from config
# Should match the one used in other managers or be passed consistently
DEFAULT_BASE_DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data"

class UserSessionManager:
    """
    Manages user-specific manager instances (ChatFile, Memory, Conversation)
    and caches them for active users.
    """
    def __init__(self, base_data_path: Optional[Path] = None):
        """
        Initializes the UserSessionManager.

        Args:
            base_data_path: The root directory for storing user data files.
                            Defaults to 'data/' in the project root.
        """
        self.base_data_path = base_data_path or DEFAULT_BASE_DATA_PATH
        # Ensure base path exists (optional, as managers might do it too)
        try:
             self.base_data_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
             logger.error(f"Failed to ensure base data path {self.base_data_path}: {e}", exc_info=True)
             # Decide if this is critical - maybe allow proceeding if managers handle it

        # --- User-Scoped Manager Cache ---
        self._user_managers_cache: Dict[int, Dict[str, Any]] = {}
        logger.info(f"UserSessionManager initialized. Base data path: {self.base_data_path}")
        # TODO: Add mechanism to clear inactive users/sessions from this cache periodically

    def _initialize_user_entry(self, user_id: int) -> None:
        """Initializes the cache entry for a user, including managers."""
        if user_id in self._user_managers_cache:
            return # Already initialized

        logger.info(f"Initializing managers and session cache for user: {user_id}")
        try:
            # Instantiate managers with required config (user_id, base_data_path)
            # Order matters if there are dependencies (e.g., CMM needs EMM)
            episodic_mem = EpisodicMemoryManager(
                user_id=user_id
            )
            cfm = ChatFileManager()
            cmm = ContextualMemoryManager(
                user_id=user_id,
                episodic_memory_manager=episodic_mem
            )

            self._user_managers_cache[user_id] = {
                "cfm": cfm,
                "cmm": cmm,
                "episodic": episodic_mem,
                "chat_sessions": {}, # Initialize empty dict for ConversationManagers
                "last_activity": time.time()
            }
            logger.info(f"Successfully initialized and cached managers for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize managers for user {user_id}: {e}", exc_info=True)
            if user_id in self._user_managers_cache: # Clean up partial entry
                 del self._user_managers_cache[user_id]
            raise RuntimeError(f"Manager initialization failed for user {user_id}") from e

    def get_user_managers(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieves the core data/memory manager instances scoped to the given user_id.
        Initializes the user entry in the cache if it doesn't exist.
        Assumes user_id is valid (validated upstream by AuthService).

        Returns:
            A dictionary containing the manager instances:
            {"cfm": ChatFileManager, "cmm": ContextualMemoryManager, "episodic": EpisodicMemoryManager}

        Raises:
            RuntimeError: If manager initialization fails.
            ValueError: If user_id is invalid (basic check).
        """
        if not isinstance(user_id, int) or user_id <= 0:
             logger.error(f"Invalid user_id type or value received: {user_id} ({type(user_id)})")
             raise ValueError("Invalid user_id provided to get_user_managers")

        if user_id not in self._user_managers_cache:
            self._initialize_user_entry(user_id) # Can raise RuntimeError
        else:
            logger.debug(f"Retrieved cached managers for user: {user_id}")
            self._user_managers_cache[user_id]["last_activity"] = time.time() # Update activity

        managers = self._user_managers_cache[user_id]
        return {
            "cfm": managers["cfm"],
            "cmm": managers["cmm"],
            "episodic": managers["episodic"]
        }

    def get_conversation_manager(self, user_id: int, session_id: Optional[str] = None) -> Tuple[Optional[str], Optional[ConversationManager]]:
        """
        Retrieves or creates a ConversationManager instance for a specific chat session
        belonging to the given user. Handles caching of ConversationManager instances.

        Args:
            user_id: The ID of the authenticated user.
            session_id: The specific chat session ID. If None, a new session is created.

        Returns:
            A tuple containing: (actual_session_id, conversation_manager_instance) or (None, None) on failure.

        Raises:
            ValueError: If user_id is invalid (basic check).
            RuntimeError: If manager initialization fails.
        """
        logger.debug(f"Entering get_conversation_manager for user {user_id}, requested session_id: {session_id}")
        if not isinstance(user_id, int) or user_id <= 0:
            logger.error(f"Invalid user_id received in get_conversation_manager: {user_id}")
            raise ValueError("Invalid user_id provided to get_conversation_manager")

        # Ensure the user entry and core managers are initialized/cached
        try:
            user_managers = self.get_user_managers(user_id) # This initializes if needed
        except RuntimeError as e:
             logger.error(f"Failed to get/initialize core managers for user {user_id}: {e}", exc_info=True)
             return None, None # Cannot proceed

        user_entry = self._user_managers_cache[user_id]
        chat_sessions_cache = user_entry["chat_sessions"]

        # --- Session Handling ---

        # If a specific session is requested and exists in cache
        if session_id and session_id in chat_sessions_cache:
            logger.debug(f"Retrieved cached ConversationManager for user {user_id}, session {session_id}")
            cached_cm = chat_sessions_cache[session_id]
            # Ensure the cached CM's current_session matches the requested one (it should)
            if cached_cm.current_session_id != session_id:
                 logger.warning(f"Cached CM session mismatch! Expected {session_id}, got {cached_cm.current_session_id}. Reloading.")
                 # Reload the correct session context within the cached CM instance
                 if not cached_cm.load_chat(session_id):
                      logger.error(f"Failed to reload correct session {session_id} into cached CM instance.")
                      # What to do here? Maybe remove from cache and force re-creation?
                      del chat_sessions_cache[session_id]
                      # Fall through to re-create logic below
                 else:
                      return session_id, cached_cm # Return after successful reload
            else:
                 return session_id, cached_cm # Return cached instance

        # If session not in cache, need to instantiate or load
        logger.info(f"Instantiating ConversationManager for user {user_id}.")
        try:
            cm = ConversationManager(
                user_id=user_id,
                contextual_memory_manager=user_managers["cmm"],
                episodic_memory_manager=user_managers["episodic"],
                chat_file_manager=user_managers["cfm"]
            )

            actual_session_id = None
            if session_id:
                # Attempt to load the requested session
                logger.info(f"Attempting to load session {session_id} into new CM instance.")
                if cm.load_chat(session_id):
                    actual_session_id = session_id
                    logger.info(f"Successfully loaded session {session_id}.")
                else:
                    logger.warning(f"Failed to load requested session {session_id}. Starting a new chat instead.")
                    # Fall through to start_new_chat
            else:
                 logger.info("No session_id provided. Starting a new chat.")
                 # Fall through to start_new_chat

            # If no specific session loaded successfully, start a new one
            if not actual_session_id:
                 actual_session_id = cm.start_new_chat()
                 if not actual_session_id:
                      raise RuntimeError("ConversationManager failed to start a new chat.")

            # Cache the newly created/loaded CM instance
            chat_sessions_cache[actual_session_id] = cm
            logger.info(f"Cached ConversationManager for user {user_id}, session {actual_session_id}")
            return actual_session_id, cm

        except Exception as e:
            logger.exception(f"!!! FAILED to instantiate or load session in ConversationManager for user {user_id}, requested session {session_id} !!!")
            # Don't raise here, return None, None to indicate failure to caller
            return None, None


    def clear_user_cache(self, user_id: int):
        """Removes a user's cached managers and chat sessions."""
        if user_id in self._user_managers_cache:
            logger.info(f"Clearing cache for user {user_id}")
            # Potentially add cleanup logic for managers if needed (e.g., closing files)
            user_entry = self._user_managers_cache[user_id]
            # Example cleanup (if managers have close methods)
            # if user_entry.get("cfm") and hasattr(user_entry["cfm"], "close"): user_entry["cfm"].close()
            # ... etc ...

            del self._user_managers_cache[user_id]
            logger.info(f"Cleared cache for user {user_id}")

    def clear_all_user_caches(self):
        """Clears all cached user managers and chat sessions."""
        logger.info("Clearing all cached user managers and sessions.")
        user_ids = list(self._user_managers_cache.keys())
        for user_id in user_ids:
            self.clear_user_cache(user_id)
        self._user_managers_cache.clear() # Ensure cache is empty
        logger.info("Finished clearing all user caches.")

# --- Optional: Add periodic cleanup logic here ---
# (Keep example commented out as before)