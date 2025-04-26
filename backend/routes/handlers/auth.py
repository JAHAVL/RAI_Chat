"""
Authentication handlers for API routes.

This module contains handlers for login, registration, and other auth-related endpoints.
"""

import logging
from flask import request, g
from utils.auth_utils import authenticate_user, register_user, generate_token
from .common import create_error_response, create_success_response

# Create logger
logger = logging.getLogger(__name__)

def handle_login():
    """Handler for user login"""
    try:
        data = request.get_json()
        
        # Validate request data
        if not data or 'email' not in data or 'password' not in data:
            logger.warning("Login attempt with missing credentials")
            return create_error_response('Email and password are required')
        
        email = data['email']
        password = data['password']
        
        # Authenticate user
        logger.info(f"Login attempt for user: {email}")
        user_data = authenticate_user(email, password)
        
        if not user_data:
            logger.warning(f"Failed login attempt for user: {email}")
            return create_error_response('Invalid email or password', 401)
        
        # Generate JWT token
        token = generate_token(user_data['user_id'], user_data['username'])
        
        # Return user info and token
        return create_success_response({
            'token': token,
            'user': user_data,
            'message': 'Login successful'
        })
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return create_error_response(f'Error during login: {str(e)}', 500)

def handle_register():
    """Handler for user registration"""
    try:
        data = request.get_json()
        
        # Validate request data
        if not data or 'username' not in data or 'email' not in data or 'password' not in data:
            return create_error_response('Username, email, and password are required')
        
        username = data['username']
        email = data['email']
        password = data['password']
        
        # Create the user
        logger.info(f"Registration attempt for username: {username}, email: {email}")
        user_data = register_user(username, email, password)
        
        if not user_data:
            error_msg = f"Failed registration: Username or email already exists"
            logger.warning(error_msg)
            return create_error_response(error_msg)
        
        # Generate JWT token
        token = generate_token(user_data['user_id'], user_data['username'])
        
        # Return user info and token
        return create_success_response({
            'token': token,
            'user': user_data,
            'status': 'success',
            'message': 'Registration successful'
        })
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        return create_error_response(f'Error during registration: {str(e)}', 500)

def handle_logout():
    """Handler for user logout"""
    try:
        # JWT tokens are stateless, so we just return success
        # In a real-world app, you might want to blacklist the token
        return create_success_response({
            'message': 'Logout successful'
        })
    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        return create_error_response(f'Error during logout: {str(e)}', 500)

def handle_get_current_user():
    """Handler to get current user info"""
    try:
        # User info is stored in g.user by the token_required decorator
        return create_success_response({
            'user': {
                'username': g.user['username'],
                'user_id': g.user['user_id']
            }
        })
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}", exc_info=True)
        return create_error_response(f'Error retrieving user info: {str(e)}', 500)
