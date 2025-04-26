# RAI_Chat/backend/managers/memory/context_builder.py

import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime
import re
import math

# Import the Message model directly
from models.message import Message

from sqlalchemy.orm import Session as SQLAlchemySession

logger = logging.getLogger(__name__)

class ContextBuilder:
    """
    Builds conversation context based on tiered memory approach.
    """
    
    # Constant for estimating tokens (GPT tokenization approximation)
    AVG_TOKENS_PER_CHAR = 0.25
    MAX_CONTEXT_TOKENS = 4000  # Default max tokens for context
    
    def __init__(self, db_session: SQLAlchemySession, tier_manager=None):
        """
        Initialize the ContextBuilder with database session and optional tier manager.
        
        Args:
            db_session: SQLAlchemy database session
            tier_manager: Optional tier manager instance
        """
        self.db = db_session
        self.tier_manager = tier_manager
        self.logger = logging.getLogger(__name__)
        logger.info("ContextBuilder initialized")
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text using character count.
        More precise than word count for most tokenizers.
        
        Args:
            text: The text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return math.ceil(len(text) * self.AVG_TOKENS_PER_CHAR)
    
    def build_tiered_context(self, 
                           current_message: str, 
                           session_id: str, 
                           user_id: int, 
                           include_episodic: bool = False,
                           episodic_context: Optional[str] = None) -> str:
        """
        Build context with appropriate tier levels for each message in history.
        
        Args:
            current_message: The user's current message
            session_id: The session ID
            user_id: The user ID
            include_episodic: Whether to include episodic memory
            episodic_context: Optional episodic memory context to include
            
        Returns:
            Complete context string for LLM
        """
        # Get all messages in this session
        messages = self.db.query(Message)\
                     .filter_by(session_id=session_id)\
                     .order_by(Message.timestamp.asc())\
                     .all()
        
        # Start building context
        context_parts = []
        
        # Add header with current time and instructions
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        context_parts.append(f"Current time: {current_time}\n")
        
        # Add tier system explanation
        context_parts.append(self._get_tier_system_explanation())
        
        # Add conversation history with appropriate tiers
        history_parts = []
        
        for i, msg in enumerate(messages):
            # Skip the newest message if it matches the current message (avoid duplication)
            if i == len(messages) - 1 and msg.role == "user" and msg.content == current_message:
                continue
                
            # Get content based on required tier level
            if msg.required_tier_level == 1 and msg.tier1_content:
                content = msg.tier1_content
                tier_level = 1
            elif msg.required_tier_level == 2 and msg.tier2_content:
                content = msg.tier2_content
                tier_level = 2
            else:
                content = msg.content
                tier_level = 3
            
            # Format the message with tier level indicator
            message_dict = {
                "role": msg.role,
                "content": content,
                "message_id": msg.message_id
            }
            msg_formatted = self.format_message(message_dict)
            
            if tier_level == 1:
                # Just show the minimal content for tier 1
                history_parts.append(msg_formatted)
            else:
                # Add more details for higher tiers
                created_at = msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else "Unknown time"
                history_parts.append(f"{msg_formatted} (Tier {tier_level}, {created_at})")
        
        # Add the conversation history
        if history_parts:
            context_parts.append("CONVERSATION HISTORY:\n" + "\n\n".join(history_parts))
        
        # Add episodic memory if available
        if include_episodic and episodic_context:
            context_parts.append(f"RELEVANT_EPISODIC_MEMORY:\n{episodic_context}")
        
        # Add the current message
        context_parts.append(f"CURRENT_MESSAGE:\n{current_message}")
        
        # Combine all parts
        return "\n\n".join(context_parts)
    
    def build_context(self, messages: List[Dict[str, Any]], max_tokens: int = None) -> str:
        """
        Build context from messages with token awareness.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to include in context (default: self.MAX_CONTEXT_TOKENS)
            
        Returns:
            Formatted context string
        """
        if max_tokens is None:
            max_tokens = self.MAX_CONTEXT_TOKENS
            
        self.logger.info(f"Building context with max tokens: {max_tokens}")
        
        # Start with system context parts
        context_parts = [self._get_tier_system_explanation()]
        token_budget = max_tokens - self.estimate_tokens(context_parts[0])
        
        # Track token usage during building
        used_tokens = 0
        history_parts = []
        tier_counts = {1: 0, 2: 0, 3: 0}
        
        # Process messages in reverse to prioritize recent messages
        for msg in reversed(messages):
            # Skip if no content
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            if not content:
                continue
                
            # Get required tier level
            tier_level = msg.required_tier_level if hasattr(msg, 'required_tier_level') else 1
            
            # Format the message
            message_dict = {
                "role": msg.role if hasattr(msg, 'role') else msg.get('role', 'unknown'),
                "content": content,
                "message_id": msg.message_id if hasattr(msg, 'message_id') else msg.get('message_id', 'unknown_id')
            }
            
            # Format with time info based on tier
            if tier_level > 1:
                created_at = msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(msg, 'created_at') and msg.created_at else "Unknown time"
                formatted_msg = f"{self.format_message(message_dict)} (Tier {tier_level}, {created_at})"
            else:
                formatted_msg = self.format_message(message_dict)
                
            # Calculate tokens for this message
            msg_tokens = self.estimate_tokens(formatted_msg)
            
            # Only add if we have enough token budget
            if used_tokens + msg_tokens <= token_budget:
                history_parts.append((formatted_msg, tier_level))  # Keep tier for sorting
                used_tokens += msg_tokens
                tier_counts[tier_level] = tier_counts.get(tier_level, 0) + 1
            elif tier_level > 1:
                # Always try to include higher tier messages - drop lower tier if needed
                if history_parts:
                    # Find the lowest tier message
                    lowest_tier_idx = min(range(len(history_parts)), key=lambda i: history_parts[i][1])
                    lowest_tier_msg, lowest_tier = history_parts[lowest_tier_idx]
                    
                    if lowest_tier < tier_level:
                        # Drop the lowest tier message and add this higher tier one
                        lowest_tier_tokens = self.estimate_tokens(lowest_tier_msg)
                        if used_tokens - lowest_tier_tokens + msg_tokens <= token_budget:
                            del history_parts[lowest_tier_idx]
                            history_parts.append((formatted_msg, tier_level))
                            used_tokens = used_tokens - lowest_tier_tokens + msg_tokens
                            tier_counts[lowest_tier] = tier_counts.get(lowest_tier, 0) - 1
                            tier_counts[tier_level] = tier_counts.get(tier_level, 0) + 1
                            self.logger.info(f"Prioritized tier {tier_level} message over tier {lowest_tier} message")
            
            # Stop if we've processed enough messages
            if used_tokens >= token_budget:
                self.logger.info(f"Reached token budget: {used_tokens}/{token_budget}")
                break
                
        # Add the conversation history from newest to oldest
        # Sort by tier level (desc) and then by position (to maintain chronological order within tiers)
        if history_parts:
            # Extract just the formatted messages, preserving original order for same-tier messages
            # Higher tier messages come first within their timestamp position
            formatted_history = []
            for i, (msg, _) in enumerate(history_parts):
                formatted_history.append(msg)
                
            # Add to context parts
            if formatted_history:
                context_parts.append("\n".join(formatted_history))
        
        # Log the context stats
        self.logger.info(f"Built context with {used_tokens} tokens. Tier distribution: {tier_counts}")
        
        # Combine all parts
        return "\n\n".join(context_parts)
    
    def format_message(self, message: Dict[str, Any], include_id: bool = True) -> str:
        """
        Format a message for context building.
        
        Args:
            message: The message to format
            include_id: Whether to include the message ID in the formatted message
            
        Returns:
            The formatted message
        """
        # Extract message fields
        role = message.get("role", "unknown")
        content = message.get("content", "")
        message_id = message.get("message_id", "unknown_id")
        
        # Ensure message ID is properly formatted for tier requests
        if include_id:
            # Always start with msg_ prefix for consistency, ensuring LLM can easily identify it
            if not message_id.startswith("msg_") and not message_id.startswith("message_"):
                message_id = f"msg_{message_id}"
                
            # Make ID very prominent with special format for easy identification by LLM
            formatted = f"[Message ID: {message_id}] {role.capitalize()}: {content}"
        else:
            formatted = f"{role.capitalize()}: {content}"
            
        return formatted
    
    def _get_tier_system_explanation(self) -> str:
        """
        Return the explanation of the tier system for the LLM.
        """
        return """
        CONVERSATION CONTEXT SYSTEM:
        The conversation history is provided with different detail levels (tiers):
        - Tier 1: Ultra-concise summary (key topics only)
        - Tier 2: Detailed summary (main points and some details)
        - Tier 3: Complete original content (full details)
        
        CRITICAL MEMORY INSTRUCTIONS:
        1. When asked about ANY fact previously mentioned by the user, you MUST request higher tier information
        2. For general context, use [REQUEST_TIER:2:message_id] and for specific facts use [REQUEST_TIER:3:message_id]
        3. The system prunes older messages after reaching a token limit - if information isn't in current context, use [SEARCH_EPISODIC:keyword]
        4. If the user asks "what is my X" or "what did I say about X", IMMEDIATELY use both tier requests and episodic search
        5. NEVER guess or make up facts - if information isn't in your current context, request it
        6. ALWAYS treat tier upgraded content as absolute truth and fully incorporate it in your response
        7. Every time a user asks about a fact, use AT LEAST ONE tier request or episodic search command
        8. REMEMBER: It is BETTER to request tier upgrades too aggressively than to miss information
        
        Request higher tiers or search episodic memory IMMEDIATELY when needed - don't waste tokens explaining that you don't know!
        """
