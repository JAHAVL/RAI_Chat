"""
Authentication Manager for RAI Chat Backend

Handles user authentication, registration, and token operations.
"""

import os
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import g, request, jsonify
from typing import Dict, Any, Optional, Callable, TypeVar, cast

from models import User
from models.connection import get_db

# Set up logging
logger = logging.getLogger(__name__)

# Type variables for better typing
F = TypeVar('F', bound=Callable[..., Any])

class AuthenticationManager:
    """
    Handles user authentication, token generation and verification.
    """
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY') or 'development-secret-key'
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 24  # Token validity period
    
    @classmethod
    def hash_password(cls, password: str) -> bytes:
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
    
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
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
    
    @classmethod
    def generate_token(cls, user_id: int, username: str) -> str:
        """
        Generate a JWT token for a user.
        
        Args:
            user_id: User ID
            username: Username
            
        Returns:
            JWT token as string
        """
        expiration = datetime.utcnow() + timedelta(hours=cls.JWT_EXPIRATION_HOURS)
        
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': expiration
        }
        
        token = jwt.encode(
            payload,
            cls.JWT_SECRET_KEY,
            algorithm=cls.JWT_ALGORITHM
        )
        
        # jwt.encode can return bytes or string depending on the JWT version
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token
    
    @classmethod
    def verify_token(cls, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            jwt.PyJWTError: If token is invalid
        """
        return jwt.decode(
            token,
            cls.JWT_SECRET_KEY,
            algorithms=[cls.JWT_ALGORITHM]
        )
    
    @classmethod
    def token_required(cls, f: F) -> F:
        """
        Decorator to protect routes with JWT authentication.
        Places the current user in Flask's g.user
        
        Usage:
            @token_required
            def protected_route():
                # Access current user with g.user
        """
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            token = None
            
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
            if not token:
                return jsonify({
                    'status': 'error',
                    'message': 'Token is missing'
                }), 401
            
            try:
                # Decode token
                payload = cls.verify_token(token)
                
                # Set user info in Flask's g object
                g.user = {
                    'user_id': payload['user_id'],
                    'username': payload['username']
                }
                
                # Check if user still exists and is active
                with get_db() as db:
                    user = db.query(User).filter(User.user_id == payload['user_id']).first()
                    if not user or not user.is_active:
                        return jsonify({
                            'status': 'error',
                            'message': 'User account disabled or deleted'
                        }), 401
                
            except jwt.PyJWTError as e:
                logger.warning(f"Token verification failed: {e}")
                return jsonify({
                    'status': 'error',
                    'message': 'Token is invalid or expired'
                }), 401
            
            return f(*args, **kwargs)
        
        return cast(F, decorated)
    
    @classmethod
    def authenticate_user(cls, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        with get_db() as db:
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                return None
            
            if not cls.verify_password(password, user.hashed_password):
                return None
            
            return user
    
    @classmethod
    def register_user(cls, username: str, email: str, password: str) -> Optional[User]:
        """
        Register a new user.
        
        Args:
            username: Username
            email: Email address
            password: Plain text password
            
        Returns:
            Newly created User object if successful, None if user already exists
        """
        with get_db() as db:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                return None
            
            # Create new user
            hashed_password = cls.hash_password(password).decode('utf-8')
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
            
            return new_user
