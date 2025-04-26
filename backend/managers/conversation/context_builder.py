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
            
        # Adapt parameters to the memory system's context builder interface
        # The memory system's build_tiered_context expects different parameters
        try:
            # Get user_id from memory_manager
            user_id = None
            if self.memory_manager:
                user_id = self.memory_manager.user_id
            
            if not user_id:
                self.logger.error("Cannot build context: missing user_id")
                return {
                    "messages": [],
                    "relevant_facts": [],
                    "tier1_messages": [],
                    "tier2_messages": [],
                    "tier3_messages": []
                }
            
            # Try different ways to get context from the memory system
            context_result = None
            
            # Try the first approach - using build_tiered_context with all parameters
            try:
                context_result = self.context_builder.build_tiered_context(
                    current_message=user_input or "",
                    session_id=session_id,
                    user_id=user_id,
                    include_episodic=False,
                    episodic_context=None
                )
                self.logger.info("Successfully built context using memory system's build_tiered_context")
            except Exception as e1:
                self.logger.warning(f"Primary context building approach failed: {str(e1)}")
                
                # Try second approach - using build_tiered_context with minimal parameters
                try:
                    # Some implementations might just need session_id and user_input
                    context_result = self.context_builder.build_tiered_context(
                        session_id=session_id,
                        user_input=user_input
                    )
                    self.logger.info("Successfully built context using simplified parameters")
                except Exception as e2:
                    self.logger.warning(f"Secondary context building approach failed: {str(e2)}")
                    
                    # Try third approach - using build_context if available
                    try:
                        if hasattr(self.context_builder, 'build_context'):
                            # Check if the memory system has a simpler build_context method
                            messages = []
                            if self.memory_manager and hasattr(self.memory_manager, 'get_messages_for_session'):
                                messages = self.memory_manager.get_messages_for_session(session_id)
                            context_result = self.context_builder.build_context(messages)
                            self.logger.info("Successfully built context using memory system's build_context")
                    except Exception as e3:
                        self.logger.error(f"All context building approaches failed: {str(e3)}")
                        
                        # If we get here, we need a fallback implementation
                        self.logger.warning("Using fallback context building implementation")
                        if self.memory_manager:
                            # Try to get context directly from memory manager
                            summary = ""
                            if hasattr(self.memory_manager, 'get_context_summary'):
                                summary = self.memory_manager.get_context_summary()
                            
                            # Format basic context
                            context_result = f"Session: {session_id}\nUser input: {user_input or ''}\nContext summary: {summary}"
            
            # If we have a result, format it appropriately
            if context_result:
                # Handle string result
                if isinstance(context_result, str):
                    return {
                        "messages": [{"role": "system", "content": context_result}],
                        "relevant_facts": [],
                        "tier1_messages": [],
                        "tier2_messages": [],
                        "tier3_messages": []
                    }
                # Handle dict result
                elif isinstance(context_result, dict):
                    return context_result
            
            # If we got here, we couldn't get any context
            self.logger.error("Failed to build context using any available approach")
            return {
                "messages": [{"role": "system", "content": f"Current session: {session_id}. Failed to retrieve context."}],
                "relevant_facts": [],
                "tier1_messages": [],
                "tier2_messages": [],
                "tier3_messages": []
            }
                
        except Exception as e:
            self.logger.error(f"Error adapting parameters for context builder: {str(e)}")
            return {
                "messages": [],
                "relevant_facts": [],
                "tier1_messages": [],
                "tier2_messages": [],
                "tier3_messages": []
            }
        
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
            
        # In the refactored memory manager, all message types go through process_user_message
        # The content value is all we need since the method handles constructing the message object
        content = message.get('content', '')
        if content:
            self.memory_manager.process_user_message(session_id, content)
        else:
            self.logger.warning("Empty message content, not adding to context")
            
    def extract_and_store_facts(self, content: str, session_id: str) -> None:
        """
        Extract and store facts from content.
        
        Args:
            content: Content to extract facts from
            session_id: Session to associate facts with
        """
        if not self.memory_manager:
            return
            
        # In the refactored memory manager, fact extraction is integrated into process_user_message
        self.memory_manager.process_user_message(session_id, content)