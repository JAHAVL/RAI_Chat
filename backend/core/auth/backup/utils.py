# RAI_Chat/backend/core/auth/utils.py
"""
Authentication utilities for the RAI Chat application.

This file provides core authentication functions used throughout the application:
1. Password hashing and verification
2. JWT token functionality
3. Authentication decorator for API endpoints

It intentionally avoids circular imports by directly accessing the database.
"""

import bcrypt
import logging
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g, current_app
import os
import sys

# Fix imports by using absolute imports with fallback mechanism
try:
    # First try absolute import
    from backend.core.database.connection import get_db
    from backend.core.database.models import User
    from backend.core.auth.models import UserSchema
except ImportError:
    # Add backend directory to path if needed
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, '../..'))
    
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    # Try direct import
    from core.database.connection import get_db
    from core.database.models import User 
    from core.auth.models import UserSchema

logger = logging.getLogger(__name__)

def hash_password(password: str) -> bytes:
    """Hash a password using bcrypt."""
    if not password:
        logger.warning("Attempting to hash an empty password.")
        raise ValueError("Password cannot be empty")
    
    try:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)
    except Exception as e:
        logger.error(f"Error hashing password: {e}", exc_info=True)
        raise

def verify_password(hashed_password_bytes: bytes, provided_password: str) -> bool:
    """Verify a provided password against a stored hash."""
    if not provided_password or not hashed_password_bytes:
        return False
        
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), hashed_password_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def generate_token(user_id: int, username: str, expiry_hours: int = 24) -> str:
    """Generate a JWT token for a user."""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=expiry_hours)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def token_required(f):
    """Decorator to require token authentication for API endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Development mode auto-authentication
        if current_app.config.get('DEV_AUTO_AUTH', False):
            with get_db() as db:
                user = db.query(User).filter(User.user_id == 1).first()
                if user:
                    g.current_user = UserSchema.from_orm(user)
                    logger.debug(f"Auto-authenticated as user: {user.username}")
                    return f(*args, **kwargs)
        
        # Standard token authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Authentication required"}), 401
            
        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(
                token, 
                current_app.config['SECRET_KEY'], 
                algorithms=['HS256']
            )
            
            # Get user from database
            with get_db() as db:
                user = db.query(User).filter(User.user_id == payload.get('user_id')).first()
                if not user:
                    return jsonify({"error": "User not found"}), 401
                    
                g.current_user = UserSchema.from_orm(user)
                
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({"error": "Invalid authentication"}), 401
            
    return decorated