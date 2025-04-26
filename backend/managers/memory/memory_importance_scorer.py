"""
Memory importance scorer for RAI Chat.
Inspired by Windsurf/Cascade's memory management techniques.
"""

import re
import math
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryImportanceScorer:
    """
    Scores memory items for importance using multiple factors:
    - Recency: How recent the message is
    - Content relevance: How relevant the content is to user's interests/goals
    - Interaction signal: User engagement with the information
    - Semantic importance: Whether it contains key facts/instructions
    
    This helps automatically determine which messages to upgrade to higher tiers.
    """
    
    # Importance indicators - words that suggest the content is important
    IMPORTANCE_INDICATORS = [
        # Personal information
        "my name is", "i am", "i'm called", "call me", 
        # Preferences
        "i prefer", "i like", "i love", "i enjoy", "i want", "i need", "i have to",
        # Instructions
        "please", "could you", "remember", "don't forget", "important", 
        # Project details
        "project", "deadline", "timeline", "feature", "requirement",
        # Personal facts
        "age", "birthday", "live in", "address", "contact", "email",
        # Technical information
        "using", "tech stack", "language", "framework", "library", "version",
        # Decision points
        "decided", "choice", "selected", "chosen", "picked"
    ]
    
    # Question indicators - suggest this might need to be referenced later
    QUESTION_INDICATORS = [
        "?", "who", "what", "when", "where", "why", "how", 
        "could you", "can you", "would you", "will you"
    ]
    
    def __init__(self):
        """Initialize the memory importance scorer."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("MemoryImportanceScorer initialized")
        
    def score_message(self, message: Dict[str, Any]) -> float:
        """
        Calculate an importance score for a message (0.0 to 1.0).
        Higher score means more important to remember.
        
        Args:
            message: The message to score
            
        Returns:
            Importance score from 0.0 to 1.0
        """
        scores = []
        
        # Get message content
        content = message.get('content', '')
        if not content:
            return 0.0
        
        # Calculate different scoring factors
        recency_score = self._calculate_recency_score(message)
        content_score = self._calculate_content_score(content)
        interaction_score = self._calculate_interaction_score(message)
        semantic_score = self._calculate_semantic_score(content)
        
        # Combine scores with appropriate weights
        # Recency is less important than semantic importance
        weighted_score = (
            recency_score * 0.2 +
            content_score * 0.3 +
            interaction_score * 0.1 +
            semantic_score * 0.4
        )
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, weighted_score))
    
    def recommend_tier(self, message: Dict[str, Any], current_tier: int = 1) -> int:
        """
        Recommend a tier level (1-3) for a message based on its importance.
        
        Args:
            message: The message to score
            current_tier: The current tier level of the message
            
        Returns:
            Recommended tier level (1-3)
        """
        importance = self.score_message(message)
        
        # Never downgrade tiers
        if importance > 0.8:
            return max(current_tier, 3)  # Very important -> Tier 3
        elif importance > 0.5:
            return max(current_tier, 2)  # Moderately important -> Tier 2
        else:
            return current_tier  # Keep current tier
    
    def should_auto_upgrade(self, message: Dict[str, Any], threshold: float = 0.8) -> bool:
        """
        Determine if a message should be automatically upgraded based on importance.
        
        Args:
            message: The message to evaluate
            threshold: The importance threshold for auto-upgrading
            
        Returns:
            True if message should be auto-upgraded
        """
        importance = self.score_message(message)
        return importance >= threshold
    
    def _calculate_recency_score(self, message: Dict[str, Any]) -> float:
        """
        Calculate a recency score (newer = more important).
        
        Args:
            message: The message to score
            
        Returns:
            Recency score from 0.0 to 1.0
        """
        # Extract timestamp
        created_at = message.get('created_at')
        if not created_at:
            return 0.5  # Neutral if no timestamp
            
        # Convert to datetime if string
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return 0.5  # Default if parsing fails
        
        # Calculate age in hours
        now = datetime.utcnow()
        if hasattr(created_at, 'timestamp'):  # datetime object
            age_hours = (now - created_at).total_seconds() / 3600
        else:
            return 0.5  # Default if can't calculate
            
        # Score based on recency (exponential decay)
        # Very recent (< 1 hour) -> high score
        # Older (> 24 hours) -> lower score
        if age_hours < 1:
            return 1.0
        elif age_hours < 24:
            return 0.8
        elif age_hours < 72:
            return 0.6
        elif age_hours < 168:  # 1 week
            return 0.4
        else:
            return 0.2
    
    def _calculate_content_score(self, content: str) -> float:
        """
        Calculate a content importance score based on keywords and patterns.
        
        Args:
            content: The content to score
            
        Returns:
            Content score from 0.0 to 1.0
        """
        if not content:
            return 0.0
            
        # Lowercase for case-insensitive matching
        content_lower = content.lower()
        
        # Count importance indicators
        indicator_count = 0
        for indicator in self.IMPORTANCE_INDICATORS:
            if indicator.lower() in content_lower:
                indicator_count += 1
        
        # Normalize score based on indicators found
        # More indicators = higher importance
        indicators_score = min(1.0, indicator_count / 5)  # Cap at 5 indicators
        
        # Length score - longer messages might contain more important info
        length_score = min(1.0, len(content) / 500)  # Cap at 500 chars
        
        # Combine content factors
        return 0.7 * indicators_score + 0.3 * length_score
    
    def _calculate_interaction_score(self, message: Dict[str, Any]) -> float:
        """
        Calculate interaction importance based on message interactions.
        
        Args:
            message: The message to score
            
        Returns:
            Interaction score from 0.0 to 1.0
        """
        # This is a placeholder for potential engagement tracking
        # In future versions, this could consider:
        # - Whether the message was referenced in later messages
        # - User clicks/selection of the message
        # - Whether assistant asked clarifying questions about this message
        return 0.5  # Neutral score for now
    
    def _calculate_semantic_score(self, content: str) -> float:
        """
        Calculate semantic importance based on content analysis.
        
        Args:
            content: The content to score
            
        Returns:
            Semantic score from 0.0 to 1.0
        """
        if not content:
            return 0.0
            
        # Lowercase for case-insensitive matching
        content_lower = content.lower()
        
        # Check for questions - they often lead to important information in responses
        question_score = 0.0
        for indicator in self.QUESTION_INDICATORS:
            if indicator.lower() in content_lower:
                question_score = 0.7  # Questions are moderately important
                break
                
        # Check for numeric data - often important 
        # (dates, versions, quantities, measurements, etc.)
        has_numeric = bool(re.search(r'\d', content))
        numeric_score = 0.8 if has_numeric else 0.0
        
        # Check for named entities (simple implementation)
        # Look for capitalized words not at the start of sentences
        entity_matches = []
        # Split by sentence endings and spaces, then check if words are capitalized
        words = re.split(r'[.!?]\s+|\s+', content)
        for word in words:
            if word and len(word) > 0 and word[0].isupper() and word.lower() != word:
                entity_matches.append(word)
        
        entity_score = min(1.0, len(entity_matches) / 3)  # Cap at 3 entities
        
        # Check for lists and structured content (often important information)
        has_list = bool(re.search(r'(?m)^[-*•]\s|\d+\.\s', content))
        list_score = 0.7 if has_list else 0.0
        
        # Return maximum of the various semantic indicators
        return max(question_score, numeric_score, entity_score, list_score)
