"""
SystemMessage model for the RAI Chat application.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from . import Base

class SystemMessage(Base):
    """SQLAlchemy model for system messages (notifications, status updates, etc.)"""
    __tablename__ = 'system_messages'
    
    id = Column(String(100), primary_key=True, default=lambda: f"sys_{str(uuid.uuid4())}")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    session_id = Column(String(36), ForeignKey('sessions.session_id'), nullable=False, index=True)
    message_type = Column(String(50), nullable=False, index=True)  # e.g., 'status_update', 'web_search', etc.
    content = Column(JSON, nullable=False)  # Stores the JSON content of the system message
    
    # Define relationships
    session = relationship("Session")
    
    def __repr__(self):
        return f"<SystemMessage(id='{self.id}', type='{self.message_type}', session_id='{self.session_id}')>"
