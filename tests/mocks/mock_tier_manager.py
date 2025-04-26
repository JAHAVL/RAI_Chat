# RAI_Chat/tests/mocks/mock_tier_manager.py

import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MockTierManager:
    """
    A mock version of TierManager for testing.
    Generates predictable tiers without relying on the LLM API.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("MockTierManager")
        self.logger.info("Mock TierManager initialized")
    
    def generate_tiers(self, message_content: str, role: str) -> Dict[str, str]:
        """
        Generate tiered representations of a message.
        
        Args:
            message_content: Original message content
            role: Message role (user, assistant, system)
            
        Returns:
            Dictionary with tier1_content and tier2_content
        """
        # For testing, we'll create simple tiers
        # Tier 1: First 10 words + "..."
        # Tier 2: First 50% of the message
        
        words = message_content.split()
        
        # Tier 1: First 10 words (or less if message is shorter)
        tier1_words = words[:min(10, len(words))]
        tier1 = " ".join(tier1_words)
        if len(words) > 10:
            tier1 += "..."
        
        # Tier 2: About half the message
        half_length = max(len(message_content) // 2, 20)  # At least 20 chars
        tier2 = message_content[:half_length]
        if len(message_content) > half_length:
            tier2 += "..."
        
        return {
            "tier1_content": tier1,
            "tier2_content": tier2
        }
    
    def generate_fallback_tiers(self, message_content: str) -> Dict[str, str]:
        """
        Generate fallback tiers for when the LLM-based generation fails.
        
        Args:
            message_content: Original message content
            
        Returns:
            Dictionary with tier1_content and tier2_content
        """
        return self.generate_tiers(message_content, "user")
