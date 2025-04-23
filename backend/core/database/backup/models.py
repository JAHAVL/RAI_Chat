# RAI_Chat/backend/core/database/models.py

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
    auth_provider = Column(String(50), nullable=False, default='local')
    email = Column(String(255), nullable=True, unique=True, index=True) # Indexed for faster lookups
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    remembered_facts = Column(JSON, nullable=True) # New field for user-level memory

    # Define the relationship to the Session model
    # 'sessions' will be a collection of Session objects related to this User
    # cascade="all, delete-orphan" means related sessions are deleted if the user is deleted
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', email='{self.email}')>"


class Session(Base):
    """SQLAlchemy model for the sessions table."""
    __tablename__ = 'sessions'

    # Using String for session_id to accommodate UUIDs or other string-based IDs
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True) # Foreign key to users table
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True) # Indexed for faster sorting/filtering
    metadata_json = Column(JSON, nullable=True) # For storing arbitrary structured metadata

    # Define the relationship back to the User model
    # 'user' will be the User object related to this Session
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(session_id='{self.session_id}', user_id={self.user_id}, title='{self.title}')>"

# Example of how to create the engine (will be done in connection.py)
# from sqlalchemy import create_engine
# DATABASE_URL = "mysql+mysqlconnector://user:password@host/db_name"
# engine = create_engine(DATABASE_URL)
# Base.metadata.create_all(engine) # Creates tables if they don't exist (Alembic is preferred for managing schema changes)