"""
Authentication middleware for RAI Chat Backend.

This module provides decorators and utilities for authenticating requests,
without interfering with core business logic like video transcript retrieval.
"""

import os
import jwt
import logging
from functools import wraps
from datetime import datetime
from flask import request, jsonify, g
from typing import Dict, Any, Callable, TypeVar, cast

from models import User
from models.connection import get_db

# Set up logging
logger = logging.getLogger(__name__)

# Type variables for better typing
F = TypeVar('F', bound=Callable[..., Any])

# JWT settings - keep in sync with utils/auth_utils.py
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY') or 'development-secret-key'
JWT_ALGORITHM = 'HS256'

def token_required(f: F) -> F:
    """
    Decorator that protects routes with JWT authentication.
    Places the current user in Flask's g.user for easy access in route handlers.
    
    This middleware runs before any route handler, ensuring all protected
    routes have proper authentication. It does not interfere with business logic
    such as video transcript retrieval, which operates after authentication.
    
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
                'message': 'Authentication required'
            }), 401
        
        try:
            # Decode token
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM]
            )
            
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
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired token attempted")
            return jsonify({
                'status': 'error',
                'message': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid token'
            }), 401
        
        return f(*args, **kwargs)
    
    return cast(F, decorated)

def dev_auth_bypass(f: F) -> F:
    """
    For development purposes only.
    Bypasses authentication and sets a mock user.
    
    This should only be used during development and testing,
    never in production environments.
    """
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        # Set a mock user in Flask's g object
        g.user = {
            'user_id': 1,
            'username': 'dev_user'
        }
        return f(*args, **kwargs)
    
    return cast(F, decorated)
