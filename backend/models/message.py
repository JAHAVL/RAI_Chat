"""
Message model for the RAI Chat application.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import relationship

from . import Base

class Message(Base):
    """
    Represents a message in a conversation with tiered content support.
    Different tiers represent varying levels of detail for efficient context management.
    """
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    message_id = Column(String(36), unique=True, index=True)  # UUID as string
    session_id = Column(String(36), index=True)  # Session UUID
    user_id = Column(Integer, index=True)  # User ID
    content = Column(Text)  # Original content (Tier 3)
    tier1_content = Column(Text, nullable=True)  # Tier 1 (key-value) version
    tier2_content = Column(Text, nullable=True)  # Tier 2 (summary) version
    required_tier_level = Column(Integer, default=1)  # Which tier level should be used by default
    role = Column(String(20))  # user, assistant, system
    timestamp = Column(DateTime, default=datetime.utcnow)
    message_metadata = Column(JSON, nullable=True)  # Any additional metadata

    def __repr__(self):
        return f"<Message(message_id='{self.message_id}', role='{self.role}')>"

    def get_tier_content(self, tier_level=None):
        """
        Get the content for the specified tier level.
        If no tier is specified, use the message's required_tier_level.
        """
        tier = tier_level or self.required_tier_level
        
        if tier == 1 and self.tier1_content:
            return self.tier1_content
        elif tier == 2 and self.tier2_content:
            return self.tier2_content
        else:
            # Default to original content (Tier 3) if requested tier is missing
            return self.content
