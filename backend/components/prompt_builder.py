# RAI_Chat/backend/components/prompt_builder.py
import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING

# Import prompts function from new location
from components.prompts import DEFAULT_SYSTEM_PROMPT

# Type hints for managers (using new paths)
if TYPE_CHECKING:
    from managers.memory.contextual_memory import ContextualMemoryManager
    from managers.memory.episodic_memory import EpisodicMemoryManager

logger = logging.getLogger(__name__)

class PromptBuilder:
    """Handles the gathering of context and construction of system prompts."""

    def __init__(self,
                 contextual_memory_manager: 'ContextualMemoryManager',
                 episodic_memory_manager: 'EpisodicMemoryManager'):
        """
        Initialize PromptBuilder with necessary memory managers.

        Args:
            contextual_memory_manager: User-scoped ContextualMemoryManager instance.
            episodic_memory_manager: User-scoped EpisodicMemoryManager instance.
        """
        self.contextual_memory = contextual_memory_manager
        self.episodic_memory = episodic_memory_manager
        # Store user_id for logging consistency
        self.user_id = contextual_memory_manager.user_id
        logger.info(f"PromptBuilder initialized for user {self.user_id}")

    def construct_prompt(self,
                         session_id: str,
                         user_input: str,
                         search_depth: int = 0,
                         web_search_results: Optional[str] = None
                         ) -> str:
        """
        Gathers context and builds the system prompt for the LLM.

        Args:
            session_id: The current session ID.
            user_input: The latest user input.
            search_depth: Current depth of episodic memory search.
            web_search_results: Optional results from a web search.

        Returns:
            The fully constructed system prompt string.
        """
        logger.info(f"Constructing prompt for session {session_id}, user {self.user_id}, depth {search_depth}")

        # --- Gather Context (Uses user-scoped managers) ---
        # This logic will be moved from ConversationManager.get_response
        current_context_summary = self.contextual_memory.get_context_summary()
        episodic_summaries = self.episodic_memory.retrieve_memories(
            user_input, limit=5
        )

        # Combine context logic
        contextual_memory_str = ""
        if current_context_summary:
            logger.info("Adding current context summary (Tier 2) to prompt.")
            contextual_memory_str = f"CURRENT_CONTEXT_SUMMARY:\n{current_context_summary}"
        else:
            logger.info("No current context summary (Tier 2) found.")

        if episodic_summaries:
            # Format the episodic summaries as a string
            episodic_summaries_str = "\n".join([f"- {summary['summary']}" for summary in episodic_summaries])
            logger.info(f"Adding {len(episodic_summaries)} episodic summaries to prompt.")
            if contextual_memory_str:
                contextual_memory_str += f"\n\nRELATED_PAST_CONVERSATIONS (Summaries):\n{episodic_summaries_str}"
            else:
                contextual_memory_str = f"RELATED_PAST_CONVERSATIONS (Summaries):\n{episodic_summaries_str}"
        else:
            logger.info(f"No episodic summaries found.")
            if search_depth > 0: logger.warning("Exhausted episodic summary search.")


        # --- Prepare other prompt arguments (Uses user-scoped managers) ---
        conversation_history_str = self.contextual_memory.get_formatted_history(limit=20)
        remember_this_str = self.contextual_memory.get_remember_this_content()
        forget_this_str = "" # No forget_this_content method in ContextualMemoryManager
        specialized_instructions_str = "" # TODO: How should this be handled? Passed in?

        # --- Build Prompt ---
        # Start with the default system prompt
        system_prompt = DEFAULT_SYSTEM_PROMPT
        
        # Add conversation history
        if conversation_history_str:
            system_prompt += f"\n\nCONVERSATION_HISTORY:\n{conversation_history_str}"
        
        # Add contextual memory
        if contextual_memory_str:
            system_prompt += f"\n\nCONTEXTUAL_MEMORY:\n{contextual_memory_str}"
        
        # Add specialized instructions
        if specialized_instructions_str:
            system_prompt += f"\n\nSPECIALIZED_INSTRUCTIONS:\n{specialized_instructions_str}"
        
        # Add remember this content
        if remember_this_str:
            system_prompt += f"\n\nREMEMBER_THIS:\n{remember_this_str}"
        
        # Add forget this content
        if forget_this_str:
            system_prompt += f"\n\nFORGET_THIS:\n{forget_this_str}"
        
        # Add web search results
        if web_search_results:
            system_prompt += f"\n\nWEB_SEARCH_RESULTS:\n{web_search_results}"
            
        logger.debug(f"Constructed system prompt (first 200 chars): {system_prompt[:200]}...")
        return system_prompt