"""
Authentication utilities for RAI Chat Backend.

Provides functions for user authentication, password hashing, and token generation.
These utilities complement the middleware/auth.py token verification.
"""

import os
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from models import User
from models.connection import get_db

# Set up logging
logger = logging.getLogger(__name__)

# JWT settings - keep in sync with middleware/auth.py
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY') or 'development-secret-key'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24  # Token validity period

def hash_password(password: str) -> bytes:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password bytes
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def generate_token(user_id: int, username: str) -> str:
    """
    Generate a JWT token for a user.
    
    Args:
        user_id: User ID
        username: Username
        
    Returns:
        JWT token as string
    """
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': expiration
    }
    
    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )
    
    # jwt.encode can return bytes or string depending on the JWT version
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user with email and password.
    
    Args:
        email: User email
        password: Plain text password
        
    Returns:
        Dictionary with user data if authentication successful, None otherwise
    """
    with get_db() as db:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            logger.warning(f"Authentication failed: no user with email {email}")
            return None
        
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: incorrect password for {email}")
            return None
        
        # Create a dictionary with user data before the session closes
        user_data = {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email
        }
        
        logger.info(f"User {email} successfully authenticated")
        return user_data

def register_user(username: str, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Register a new user.
    
    Args:
        username: Username
        email: Email address
        password: Plain text password
        
    Returns:
        Dictionary with user data if successful, None if user already exists
    """
    with get_db() as db:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            if existing_user.username == username:
                logger.warning(f"Registration failed: username {username} already exists")
            else:
                logger.warning(f"Registration failed: email {email} already exists")
            return None
        
        # Create new user
        hashed_password = hash_password(password).decode('utf-8')
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create a dictionary with user data before the session closes
        user_data = {
            'user_id': new_user.user_id,
            'username': new_user.username,
            'email': new_user.email
        }
        
        logger.info(f"User {username} ({email}) successfully registered")
        return user_data
