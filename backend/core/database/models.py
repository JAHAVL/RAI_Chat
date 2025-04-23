# RAI_Chat/backend/core/database/models.py
# Docker-specific version with relative imports

import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.mysql import INTEGER # For potential unsigned integers if needed later

# Define the base class for declarative models
Base = declarative_base()

class User(Base):
    """SQLAlchemy model for the users table."""
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True) # Indexed for faster lookups
    hashed_password = Column(String(255), nullable=True) # Nullable if using external auth primarily
    crm_user_id = Column(String(255), nullable=True, index=True) # Indexed for faster lookups
    remembered_facts = Column(JSON, nullable=True) # Added column to store user memory as JSON
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

class Session(Base):
    """SQLAlchemy model for the sessions table."""
    __tablename__ = 'sessions'
    
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    metadata_json = Column(JSON, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id={self.user_id})>"
