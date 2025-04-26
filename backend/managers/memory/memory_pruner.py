# RAI_Chat/backend/managers/memory/memory_pruner.py

import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime
import time

# Import models directly
from models.message import Message
from models.connection import get_db

from sqlalchemy.orm import Session as SQLAlchemySession

logger = logging.getLogger(__name__)

class MemoryPruner:
    """
    Manages contextual memory window size by pruning old messages
    and archiving them to episodic memory.
    """
    
    def __init__(self, 
                 db_session: SQLAlchemySession, 
                 episodic_memory_manager=None,
                 token_limit: int = 30000):
        self.db = db_session
        self.episodic_memory = episodic_memory_manager
        self.token_limit = token_limit
        self.min_messages = 5  # Minimum messages to keep in context
        logger.info(f"MemoryPruner initialized with {token_limit} token limit")
    
    def check_and_prune(self, session_id: str, user_id: int) -> bool:
        """
        Check if pruning is needed and perform it if necessary.
        
        Args:
            session_id: The session ID
            user_id: The user ID
            
        Returns:
            Whether pruning was performed
        """
        # Check current token count
        current_tokens = self._calculate_token_count(session_id)
        
        # If below limit, no pruning needed
        if current_tokens <= self.token_limit:
            return False
        
        # Calculate how many tokens to prune
        tokens_to_prune = current_tokens - self.token_limit + 5000  # Add buffer
        logger.info(f"Need to prune ~{tokens_to_prune} tokens from session {session_id}")
        
        # Perform pruning
        return self._prune_messages(session_id, user_id, tokens_to_prune)
    
    def _calculate_token_count(self, session_id: str) -> int:
        """
        Calculate approximate token count for the session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Estimated token count
        """
        # Get all messages for this session
        messages = self.db.query(Message)\
                     .filter_by(session_id=session_id)\
                     .order_by(Message.timestamp.asc())\
                     .all()
        
        # Calculate total token count
        total_tokens = 0
        for msg in messages:
            # Get content based on required tier level
            if msg.required_tier_level == 1 and msg.tier1_content:
                content = msg.tier1_content
            elif msg.required_tier_level == 2 and msg.tier2_content:
                content = msg.tier2_content
            else:
                content = msg.content
            
            # Approximate token count (chars / 4 is a common heuristic)
            msg_tokens = len(content) // 4
            total_tokens += msg_tokens
        
        logger.info(f"Session {session_id} has ~{total_tokens} tokens in memory")
        return total_tokens
    
    def _prune_messages(self, 
                      session_id: str, 
                      user_id: int, 
                      tokens_to_prune: int) -> bool:
        """
        Prune oldest messages and archive them to episodic memory.
        
        Args:
            session_id: The session ID
            user_id: The user ID
            tokens_to_prune: Target number of tokens to prune
            
        Returns:
            Whether pruning was performed
        """
        # Get all messages for this session
        messages = self.db.query(Message)\
                     .filter_by(session_id=session_id)\
                     .order_by(Message.timestamp.asc())\
                     .all()
        
        # Ensure we keep minimum number of messages
        if len(messages) <= self.min_messages:
            logger.info(f"Not enough messages ({len(messages)}) to prune")
            return False
        
        # Identify messages to prune
        messages_to_prune = []
        pruned_tokens = 0
        
        for msg in messages:
            # Stop if we would go below minimum message count
            if len(messages) - len(messages_to_prune) <= self.min_messages:
                break
            
            # Calculate tokens in this message (use original content for accurate count)
            msg_tokens = len(msg.content) // 4
            
            # Add to prune list
            messages_to_prune.append(msg)
            pruned_tokens += msg_tokens
            
            # Stop if we've pruned enough
            if pruned_tokens >= tokens_to_prune:
                break
        
        # Check if we're actually pruning anything
        if not messages_to_prune:
            logger.info("No messages identified for pruning")
            return False
        
        # Archive to episodic memory if available
        if self.episodic_memory:
            self._archive_to_episodic_memory(messages_to_prune, session_id, user_id)
        
        # Delete from contextual memory
        for msg in messages_to_prune:
            try:
                self.db.delete(msg)
            except Exception as e:
                logger.error(f"Error deleting message {msg.message_id}: {e}")
        
        # Commit changes
        try:
            self.db.commit()
            logger.info(f"Pruned {len(messages_to_prune)} messages (~{pruned_tokens} tokens)")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error committing pruned messages: {e}")
            return False
    
    def _archive_to_episodic_memory(self, 
                                 messages: List[Message], 
                                 session_id: str, 
                                 user_id: int) -> bool:
        """
        Archive messages to episodic memory.
        
        Args:
            messages: List of messages to archive
            session_id: The session ID
            user_id: The user ID
            
        Returns:
            Whether archiving was successful
        """
        if not self.episodic_memory:
            logger.warning("No episodic memory manager available for archiving")
            return False
        
        try:
            # Prepare data for archiving
            archive_data = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "user_id": user_id,
                "message_count": len(messages),
                "messages": [
                    {
                        "message_id": msg.message_id,
                        "role": msg.role,
                        "content": msg.content,  # Archive full content
                        "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, 'isoformat') else str(msg.timestamp)
                    } for msg in messages
                ]
            }
            
            # Generate a chunk ID based on timestamp
            first_msg_time = messages[0].timestamp
            if hasattr(first_msg_time, 'isoformat'):
                time_str = first_msg_time.isoformat()
            else:
                time_str = str(first_msg_time)
            
            chunk_id = f"chunk_{time_str.replace(':', '-').replace('.', '-')}"
            
            # Call episodic memory manager to archive
            success = self.episodic_memory.archive_and_summarize_chunk(
                session_id=session_id,
                chunk_id=chunk_id,
                raw_chunk_data=archive_data,
                user_id=user_id
            )
            
            if success:
                logger.info(f"Successfully archived {len(messages)} messages to episodic memory")
                return True
            else:
                logger.error("Failed to archive messages to episodic memory")
                return False
                
        except Exception as e:
            logger.error(f"Error archiving to episodic memory: {e}")
            return False
