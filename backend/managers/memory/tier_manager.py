# RAI_Chat/backend/managers/memory/tier_manager.py

import logging
import json
import re
from typing import Dict, Any, Optional, List, Union
import os
import time

try:
    # Local development import path
    from llm_client.llm_api import get_llm_api
except ImportError:
    # Docker container import path
    try:
        from llm_client.llm_api import get_llm_api
    except ImportError:
        # Define a fallback function if import fails
        def get_llm_api():
            logger.warning("Using fallback LLM API client")
            class FallbackLLMAPI:
                def generate_response(self, prompt, system_prompt=None):
                    return {"text": "LLM API not available. This is a fallback response."}
            return FallbackLLMAPI()

# Import database connection
from models.connection import get_db

logger = logging.getLogger(__name__)

class TierManager:
    """
    Manages the storage, retrieval and upgrading of tiered message content.
    Does NOT generate tiers - only uses tiers already created by main LLM.
    """
    
    def __init__(self):
        self.logger = logger
        self.logger.info("TierManager initialized")
    
    def store_message_tiers(self, message_id: str, session_id: str, user_id: int, 
                          role: str, tier1: str, tier2: str, content: str) -> bool:
        """
        Store a message with all three tiers in the database.
        
        Args:
            message_id: Unique message ID
            session_id: The session ID
            user_id: The user ID
            role: Message role (user, assistant, system)
            tier1: Tier 1 content (most concise)
            tier2: Tier 2 content (medium detail)
            content: Full message content (Tier 3)
            
        Returns:
            True if successfully stored, False otherwise
        """
        try:
            from models.message import Message
            
            # Ensure content is a string
            if isinstance(content, dict):
                if 'original_text' in content:
                    content = content['original_text']
                else:
                    content = str(content)
                    
            # Ensure tier1 is a string
            if isinstance(tier1, dict):
                if 'original_text' in tier1:
                    tier1 = tier1['original_text']
                else:
                    tier1 = str(tier1)
                    
            # Ensure tier2 is a string
            if isinstance(tier2, dict):
                if 'original_text' in tier2:
                    tier2 = tier2['original_text']
                else:
                    tier2 = str(tier2)
                    
            # Convert message_metadata to a JSON string if needed
            message_metadata = {}
            if isinstance(message_metadata, dict):
                import json
                message_metadata = json.dumps(message_metadata)
            
            # Format the timestamp as a proper datetime for MySQL
            from datetime import datetime
            current_time = datetime.now()
            
            with get_db() as db_session:
                # Create new message with all three tiers
                new_message = Message(
                    message_id=message_id,
                    session_id=session_id,
                    user_id=user_id,
                    content=content,  # Tier 3 (full content)
                    tier1_content=tier1,  # Tier 1 (most concise)
                    tier2_content=tier2,  # Tier 2 (medium detail)
                    required_tier_level=1,  # Default to Tier 1 for most efficient context
                    role=role,
                    timestamp=current_time,
                    message_metadata="{}",  # Empty JSON object as string
                    memory_status="contextual"  # Default to contextual memory
                )
                
                db_session.add(new_message)
                db_session.commit()
                
                self.logger.info(f"Stored {role} message with ID {message_id[:8]} in database")
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing message in database: {e}")
            return False
    
    def get_session_messages(self, session_id: str, limit: int = 20):
        """
        Retrieve messages for a session with their appropriate tier content.
        
        Args:
            session_id: The session ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message objects with appropriate tier content
        """
        try:
            from models.message import Message
            from sqlalchemy import desc
            
            with get_db() as db_session:
                # Get messages from database, sorted by timestamp (newest first)
                messages_query = (
                    db_session.query(Message)
                    .filter(Message.session_id == session_id)
                    .order_by(desc(Message.timestamp))
                    .limit(limit*2)  # Multiply by 2 to account for user/assistant pairs
                )
                
                messages = list(messages_query)
                messages.reverse()  # Reverse to get chronological order
                
                return messages
                
        except Exception as e:
            self.logger.error(f"Error retrieving messages from database: {e}")
            return []
    
    def upgrade_message_tier(self, message_id: str, target_tier: int) -> bool:
        """
        Upgrades a specific message to a higher tier in the database.
        
        Args:
            message_id: The ID of the message to upgrade
            target_tier: The target tier level (1, 2, or 3)
            
        Returns:
            True if successful, False if not found or invalid tier
        """
        if not message_id or target_tier not in [1, 2, 3]:
            self.logger.warning(f"Invalid parameters for tier upgrade: message_id={message_id}, target_tier={target_tier}")
            return False
            
        try:
            from models.message import Message
            
            with get_db() as db_session:
                # Find the message in the database
                message = db_session.query(Message).filter(Message.message_id == message_id).first()
                
                if not message:
                    self.logger.warning(f"Cannot upgrade tier: Message with ID {message_id} not found")
                    return False
                
                # Update the required tier level
                message.required_tier_level = target_tier
                db_session.commit()
                
                self.logger.info(f"Upgraded message {message_id[:8]} to tier {target_tier}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error upgrading message tier in database: {e}")
            return False
            
    def format_message_history(self, messages, include_tier_level=True):
        """
        Format a list of message objects into a readable history string.
        
        Args:
            messages: List of Message objects from the database or dicts with message data
            include_tier_level: Whether to include the tier level in the output
            
        Returns:
            Formatted history string
        """
        if not messages:
            return "Conversation history is empty."
            
        history_parts = []
        for message in messages:
            # Handle both SQLAlchemy model objects and dictionaries
            if isinstance(message, dict):
                role = message.get('role', 'unknown')
                message_id = message.get('message_id', 'unknown')
                required_tier_level = message.get('required_tier_level', 1)
                timestamp = message.get('timestamp')
                
                # Get content based on tier level
                if required_tier_level == 1:
                    content = message.get('tier1_content', message.get('content', ''))
                elif required_tier_level == 2:
                    content = message.get('tier2_content', message.get('content', ''))
                else:
                    content = message.get('content', '')
                    
                was_recalled = message.get('was_recalled', False)
            else:
                # Handle SQLAlchemy model object
                role = message.role
                message_id = message.message_id
                required_tier_level = message.required_tier_level
                timestamp = message.timestamp
                
                # Get content based on required tier level
                content = message.get_tier_content() if hasattr(message, 'get_tier_content') else message.content
                
                was_recalled = hasattr(message, 'was_recalled') and message.was_recalled
            
            # Format timestamp if available
            formatted_time = ""
            if timestamp:
                try:
                    from datetime import datetime
                    # Convert timestamp to datetime if it's a Unix timestamp
                    if isinstance(timestamp, (int, float)):
                        dt = datetime.fromtimestamp(timestamp)
                    else:
                        dt = timestamp
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    self.logger.error(f"Error formatting timestamp: {e}")
                    formatted_time = str(timestamp)
            
            # Format the message with role, timestamp, ID, tier level and content
            recalled_flag = " [recalled:yes]" if was_recalled else ""
            
            if include_tier_level:
                tier_level = required_tier_level
                if role == "user":
                    history_parts.append(f"User ({formatted_time}) [id:{message_id}] [tier:{tier_level}]{recalled_flag}: {content}")
                elif role == "assistant":
                    history_parts.append(f"Assistant ({formatted_time}) [id:{message_id}] [tier:{tier_level}]{recalled_flag}: {content}")
                else:
                    history_parts.append(f"{role.capitalize()} ({formatted_time}) [id:{message_id}] [tier:{tier_level}]{recalled_flag}: {content}")
            else:
                if role == "user":
                    history_parts.append(f"User ({formatted_time}) [id:{message_id}]{recalled_flag}: {content}")
                elif role == "assistant":
                    history_parts.append(f"Assistant ({formatted_time}) [id:{message_id}]{recalled_flag}: {content}")
                else:
                    history_parts.append(f"{role.capitalize()} ({formatted_time}) [id:{message_id}]{recalled_flag}: {content}")
        
        return "\n".join(history_parts)

    def get_contextual_messages(self, session_id: str, limit: int = 20):
        """
        Retrieve only contextual messages for a session.
        
        Args:
            session_id: The session ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message objects with appropriate tier content
        """
        try:
            from models.message import Message
            from sqlalchemy import desc
            
            with get_db() as db_session:
                # Get only contextual messages, sorted by timestamp
                messages_query = (
                    db_session.query(Message)
                    .filter(Message.session_id == session_id)
                    .filter(Message.memory_status == "contextual")
                    .order_by(desc(Message.timestamp))
                    .limit(limit*2)  # Multiply by 2 to account for user/assistant pairs
                )
                
                # Load all data from the database objects while session is open
                messages = []
                for message in messages_query:
                    # Create a dictionary with all needed attributes to avoid 
                    # accessing the database object after the session is closed
                    messages.append({
                        'message_id': message.message_id,
                        'role': message.role,
                        'content': message.content,
                        'tier1_content': message.tier1_content,
                        'tier2_content': message.tier2_content,
                        'required_tier_level': message.required_tier_level,
                        'timestamp': message.timestamp,
                        'memory_status': message.memory_status
                    })
                
                # Reverse to get chronological order
                messages.reverse()
                
                return messages
                
        except Exception as e:
            self.logger.error(f"Error retrieving contextual messages from database: {e}")
            return []
    
    def search_episodic_memory(self, session_id: str, query: str, limit: int = 5):
        """
        Search episodic memory for messages matching the query.
        
        Args:
            session_id: The session ID
            query: The search query
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message objects that match the query
        """
        try:
            from models.message import Message
            
            with get_db() as db_session:
                # Simple text-based search for now
                # In a real implementation, this would use vector similarity search
                messages_query = (
                    db_session.query(Message)
                    .filter(Message.session_id == session_id)
                    .filter(Message.memory_status == "episodic")
                    .filter(Message.content.ilike(f"%{query}%"))
                    .limit(limit)
                )
                
                messages = list(messages_query)
                
                # Mark messages as "recalled" for formatting
                for message in messages:
                    message.was_recalled = True
                
                return messages
                
        except Exception as e:
            self.logger.error(f"Error searching episodic memory: {e}")
            return []
    
    def recall_from_episodic(self, message_id: str) -> bool:
        """
        Recall a message from episodic memory back to contextual memory.
        
        Args:
            message_id: The ID of the message to recall
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from models.message import Message
            from datetime import datetime
            
            with get_db() as db_session:
                # Find the message in the database
                message = db_session.query(Message).filter(Message.message_id == message_id).first()
                
                if not message:
                    self.logger.warning(f"Cannot recall message: ID {message_id} not found")
                    return False
                
                if message.memory_status != "episodic":
                    self.logger.info(f"Message {message_id[:8]} is already in contextual memory")
                    return True
                
                # Update message to contextual status
                message.memory_status = "contextual"
                message.last_accessed = datetime.utcnow()
                # Increase importance score to avoid quick re-pruning
                message.importance_score += 1
                
                db_session.commit()
                
                self.logger.info(f"Recalled message {message_id[:8]} from episodic to contextual memory")
                return True
                
        except Exception as e:
            self.logger.error(f"Error recalling message from episodic memory: {e}")
            return False
    
    def move_to_episodic(self, message_ids: list) -> bool:
        """
        Move messages from contextual to episodic memory.
        
        Args:
            message_ids: List of message IDs to move
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from models.message import Message
            
            with get_db() as db_session:
                # Update all messages at once
                result = (
                    db_session.query(Message)
                    .filter(Message.message_id.in_(message_ids))
                    .update({"memory_status": "episodic"}, synchronize_session=False)
                )
                
                db_session.commit()
                
                self.logger.info(f"Moved {result} messages to episodic memory")
                return True
                
        except Exception as e:
            self.logger.error(f"Error moving messages to episodic memory: {e}")
            return False
    
    def prune_contextual_memory(self, session_id: str, max_tokens: int = 30000) -> bool:
        """
        Prune contextual memory when token limit is reached.
        Move older/less important messages to episodic memory.
        
        Args:
            session_id: The session ID
            max_tokens: Maximum tokens to keep in contextual memory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from models.message import Message
            from sqlalchemy import func
            
            with get_db() as db_session:
                # Calculate current token usage
                # This is a simplification - in reality, you'd use a proper tokenizer
                contextual_messages = (
                    db_session.query(Message)
                    .filter(Message.session_id == session_id)
                    .filter(Message.memory_status == "contextual")
                    .all()
                )
                
                # Estimate tokens (very roughly)
                current_tokens = sum(len(m.get_tier_content()) // 4 for m in contextual_messages)
                
                if current_tokens <= max_tokens:
                    return True  # No pruning needed
                
                # Calculate how many tokens to prune
                tokens_to_prune = current_tokens - max_tokens
                
                # Sort messages by importance and recency
                sorted_messages = sorted(
                    contextual_messages,
                    key=lambda m: (m.importance_score, m.last_accessed)  # Lower importance and older first
                )
                
                # Find messages to prune
                messages_to_prune = []
                tokens_pruned = 0
                
                for message in sorted_messages:
                    if tokens_pruned >= tokens_to_prune:
                        break
                    
                    # Estimate message tokens
                    message_tokens = len(message.get_tier_content()) // 4
                    
                    messages_to_prune.append(message.message_id)
                    tokens_pruned += message_tokens
                
                # Move selected messages to episodic memory
                if messages_to_prune:
                    self.move_to_episodic(messages_to_prune)
                    self.logger.info(f"Pruned {len(messages_to_prune)} messages from contextual memory")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error pruning contextual memory: {e}")
            return False
