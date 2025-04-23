#!/usr/bin/env python3
"""
Update a user's password in the RAI Chat application database.
"""

import os
import sys
import bcrypt
from pathlib import Path

# Add the project root to the Python path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import SQLAlchemy models and connection
from RAI_Chat.backend.core.database.models import User
from RAI_Chat.backend.core.database.connection import get_db

def update_user_password(username, new_password):
    """Update a user's password."""
    # Hash the new password
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    with get_db() as db:
        # Check if user exists
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"User '{username}' does not exist.")
            return False
        
        # Update password
        user.hashed_password = hashed_password
        db.commit()
        print(f"Password updated successfully for user '{username}'.")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python update_user_password.py <username> <new_password>")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    success = update_user_password(username, new_password)
    if not success:
        sys.exit(1)
