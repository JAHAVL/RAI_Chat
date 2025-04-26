"""
Database models for the RAI Chat application.

This package contains SQLAlchemy models representing database tables.
Import all models here to make them available when importing from the models package.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the Base class for all models
Base = declarative_base()

# Import all models to make them available when importing from the models package
from .user import User
from .session import Session
from .message import Message
from .system_message import SystemMessage

# Export all models
__all__ = [
    'Base',
    'User',
    'Session',
    'Message',
    'SystemMessage'
]
