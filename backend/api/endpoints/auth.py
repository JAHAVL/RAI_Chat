# RAI_Chat/backend/api/auth.py
"""
-------------------------------------------------------------------------
FILE PURPOSE (FOR NON-DEVELOPERS):

This file ONLY defines the API endpoints (access points) for authentication.
It does NOT contain the actual implementation - it's just where the
application receives login/registration requests and routes them to
the proper authentication service.

Endpoints defined here:
- /register - Accepts requests to create new user accounts
- /login - Accepts requests to verify credentials and issue login tokens

Think of this file as the front desk at a secure building that takes your
ID but passes it to the actual security department (AuthService) to verify.
The real work happens in the services that this file calls.
-------------------------------------------------------------------------
"""
import logging
from flask import Blueprint, request, jsonify

# Use absolute imports consistently for Docker environment
from core.auth.service import AuthService
from core.database.connection import get_db
from core.auth.utils import generate_token

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/register', methods=['POST'])
def register_user():
    """Register a new user and return JWT token"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'error': 'Username and password are required',
                'status': 'error'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')  # Optional
        
        # Use the database session as a context manager
        with get_db() as db:
            # Use the auth service
            auth_service = AuthService()
            
            # Create user data object for registration
            from core.auth.models import UserCreateSchema
            user_data = UserCreateSchema(
                username=username,
                password=password,
                email=email
            )
            
            # Call the register_user method instead of register
            user = auth_service.register_user(user_data)
            
            # Create success result format
            result = {
                'status': 'success',
                'user_id': user.user_id,  # Using user_id attribute from UserSchema
                'token': generate_token(user.user_id, user_data.username)  # Include username as required by generate_token
            }
            
            if result.get('status') == 'success':
                logger.info(f"User {username} registered successfully")
                return jsonify(result), 201
            else:
                logger.warning(f"Registration failed for username {username}")
                return jsonify(result), 400
                
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        return jsonify({
            'error': 'Registration server error',
            'status': 'error'
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login_user():
    """Log in a user and return JWT token"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'error': 'Username and password are required',
                'status': 'error'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        # Use the database session as a context manager
        with get_db() as db:
            # Use the auth service
            auth_service = AuthService()
            
            # Authenticate the user
            user = auth_service.authenticate(username, password)
            
            if user:
                # Generate token for authenticated user
                token = generate_token(user.user_id, username)
                
                # Create success response
                result = {
                    'status': 'success',
                    'user_id': user.user_id,
                    'token': token
                }
                
                logger.info(f"User {username} logged in successfully")
                return jsonify(result), 200
            else:
                logger.warning(f"Login failed for user {username}")
                return jsonify({
                    'status': 'error',
                    'error': 'Invalid credentials'
                }), 401
                
    except Exception as e:
        logger.error(f"Error logging in user: {e}", exc_info=True)
        return jsonify({
            'error': 'Authentication server error',
            'status': 'error'
        }), 500
