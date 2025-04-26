import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

class ContextBuilder:
    """
    Handles the building of context for conversation processing.
    Extracts and manages tiered context information from the conversation history.
    """
    
    def __init__(self, logger=None, context_builder=None, memory_manager=None):
        """
        Initialize the ContextBuilder.
        
        Args:
            logger: Logger instance
            context_builder: Existing context builder from memory management
            memory_manager: Memory manager for accessing history and facts
        """
        self.logger = logger or logging.getLogger(__name__)
        self.context_builder = context_builder
        self.memory_manager = memory_manager
        
    def build_tiered_context(self, session_id: str, user_input: str = None) -> Dict[str, Any]:
        """
        Build a tiered context from the conversation history and relevant facts.
        This optimizes token usage while maintaining coherence.
        
        Args:
            session_id: The current session ID
            user_input: Optional current user input to include in context
            
        Returns:
            A structured context containing tiered message history and facts
        """
        if not self.context_builder:
            self.logger.warning("No context builder available, returning minimal context")
            return {
                "messages": [],
                "relevant_facts": [],
                "tier1_messages": [],
                "tier2_messages": [],
                "tier3_messages": []
            }
            
        # Delegate to the memory system's context builder
        return self.context_builder.build_tiered_context(
            session_id=session_id,
            current_user_input=user_input
        )
        
    def add_to_conversation_context(self, message: Dict[str, Any], session_id: str) -> None:
        """
        Add a message to the conversation context.
        
        Args:
            message: The message to add
            session_id: The session to add it to
        """
        if not self.memory_manager:
            self.logger.warning("No memory manager available, cannot add to context")
            return
            
        # Determine message type and add to appropriate collection
        if message.get('role') == 'user':
            self.memory_manager.add_user_message(message, session_id)
        elif message.get('role') == 'assistant':
            self.memory_manager.add_assistant_message(message, session_id)
        elif message.get('role') == 'system':
            self.memory_manager.add_system_message(message, session_id)
        else:
            self.logger.warning(f"Unknown message role: {message.get('role')}")
            
    def extract_and_store_facts(self, content: str, session_id: str) -> None:
        """
        Extract and store facts from content.
        
        Args:
            content: Content to extract facts from
            session_id: Session to associate facts with
        """
        if not self.memory_manager:
            return
            
        self.memory_manager.extract_and_store_facts(content, session_id)