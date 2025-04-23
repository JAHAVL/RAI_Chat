# RAI_Chat/backend/core/auth/utils.py
"""
Authentication utilities for the RAI Chat application.

This file provides core authentication functions used throughout the application:
1. Password hashing and verification
2. JWT token functionality
3. Authentication decorator for API endpoints

Docker-specific version with relative imports.
"""

import bcrypt
import logging
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g, current_app
import os

# Import using relative imports for Docker
from ..database.connection import get_db
from ..database.models import User
from .models import UserSchema

logger = logging.getLogger(__name__)

def hash_password(password: str) -> bytes:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        The hashed password as bytes
    """
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

def verify_password(provided_password: str, hashed_password) -> bool:
    """
    Verify a provided password against a stored hash.
    
    Args:
        provided_password: The plain text password to verify
        hashed_password: The stored hash to check against (can be string or bytes)
        
    Returns:
        True if the password matches, False otherwise
    """
    # Handle string or bytes for hashed_password
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
        
    # Check if the provided password matches the stored hash
    return bcrypt.checkpw(provided_password.encode('utf-8'), hashed_password)

def generate_token(user_id: int, username: str, expiry_hours: int = 24) -> str:
    """
    Generate a JWT token for a user.
    
    Args:
        user_id: The ID of the user
        username: The username of the user
        expiry_hours: The number of hours until the token expires
        
    Returns:
        The generated JWT token
    """
    # Get the secret key from environment or app config
    secret_key = os.environ.get('JWT_SECRET', 'dev-secret-key')
    
    # Set the expiration time
    expiry = datetime.utcnow() + timedelta(hours=expiry_hours)
    
    # Create the payload
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': expiry
    }
    
    # Generate the token
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    
    return token

def token_required(f):
    """
    Decorator to ensure a valid token is provided for protected endpoints.
    All authenticated users have the same permission level regardless of their identity.
    
    Args:
        f: The function to decorate
        
    Returns:
        The decorated function that verifies authentication
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if we're in development mode with auto-auth enabled
        if os.environ.get('DEV_AUTO_AUTH', 'false').lower() == 'true':
            # Get user information from headers if available (for testing different users)
            # This lets us test different users while in auto-auth mode
            user_id = None
            username = None
            
            if 'X-Test-User-ID' in request.headers:
                try:
                    user_id = int(request.headers['X-Test-User-ID'])
                    username = request.headers.get('X-Test-Username', f'user_{user_id}')
                except (ValueError, TypeError):
                    pass
            
            # Default test user if not specified in headers
            if user_id is None:
                user_id = 5  # Default to testuser5
                username = "testuser5"
                
            logger.info(f"DEV_AUTO_AUTH enabled - auto-authenticating as user {username} (ID: {user_id})")
            
            # Create a User object for compatibility
            class MockUser:
                def __init__(self, user_id, username):
                    self.user_id = user_id
                    self.username = username
            
            # Set both g.user and g.current_user for compatibility
            g.user = {'user_id': user_id, 'username': username}
            g.current_user = MockUser(user_id, username)
            return f(*args, **kwargs)
        
        # Normal token verification for production environments
        token = None
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        if not token:
            logger.warning("No token provided")
            return jsonify({
                'message': 'Token is missing',
                'status': 'error'
            }), 401
        
        try:
            # Decode the token
            secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_insecure_key')
            data = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Access user data directly from token payload
            user_id = data['user_id']
            username = data['username']
            
            # Create a User object for compatibility
            class MockUser:
                def __init__(self, user_id, username):
                    self.user_id = user_id
                    self.username = username
            
            # Store user info in Flask g object
            g.user = {'user_id': user_id, 'username': username}
            g.current_user = MockUser(user_id, username)
            
            return f(*args, **kwargs)
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return jsonify({
                'message': 'Token has expired',
                'status': 'error'
            }), 401
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return jsonify({
                'message': 'Invalid token',
                'status': 'error'
            }), 401
    
    return decorated
