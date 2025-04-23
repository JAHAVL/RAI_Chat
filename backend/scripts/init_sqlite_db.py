#!/usr/bin/env python3
"""
Initialize SQLite database for RAI Chat application.
Creates necessary tables and adds a default user.
"""

import os
import sys
import bcrypt
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import SQLAlchemy models and connection
from RAI_Chat.backend.core.database.models import Base, User
from RAI_Chat.backend.core.database.connection import engine, get_db

def init_db():
    """Initialize the database by creating all tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

def create_default_user(username, password):
    """Create a default user for testing."""
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    with get_db() as db:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists.")
            return
        
        # Create new user
        new_user = User(
            username=username,
            hashed_password=hashed_password,
            email=f"{username}@example.com",
            auth_provider='local',
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        print(f"Default user '{username}' created successfully.")

if __name__ == "__main__":
    # Initialize the database
    init_db()
    
    # Create a default user
    create_default_user("admin", "admin")
    create_default_user("jordan", "password")
    
    print("Database initialization complete.")
