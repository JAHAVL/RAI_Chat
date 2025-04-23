# RAI_Chat/Backend/core/auth/service.py
# Docker-specific version with relative imports

import logging
from datetime import datetime
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import Optional, Dict, Type

# Import core components using relative imports
from ..database.models import User as UserModel
from ..database.connection import get_db # Context manager for sessions
from .strategies import AuthStrategy, LocalStrategy, CRMStrategy # Import strategies
from .models import UserSchema, UserCreateSchema # Pydantic Schemas
from .utils import hash_password, verify_password, generate_token # Auth utilities

logger = logging.getLogger(__name__)

class AuthService:
    """
    Service layer for handling user authentication and management.
    Orchestrates the use of different authentication strategies.
    """
    def __init__(self, default_strategy: str = 'local'):
        """
        Initialize the auth service with a default strategy.
        
        Args:
            default_strategy: The name of the default strategy to use ('local' or 'crm')
        """
        self.strategies: Dict[str, Type[AuthStrategy]] = {
            'local': LocalStrategy,
            'crm': CRMStrategy
        }
        self.default_strategy = default_strategy
        
        # Ensure default strategy exists
        if default_strategy not in self.strategies:
            raise ValueError(f"Invalid default strategy: {default_strategy}")
            
        logger.info(f"AuthService initialized with default strategy: {default_strategy}")
    
    def register_user(self, user_data: UserCreateSchema) -> UserSchema:
        """
        Register a new user using the default strategy.
        
        Args:
            user_data: The user data for registration
            
        Returns:
            The registered user data
            
        Raises:
            ValueError: If registration fails
        """
        # Get the appropriate strategy
        strategy_class = self.strategies[self.default_strategy]
        strategy = strategy_class()
        
        # Use context manager for database session
        with get_db() as db:
            # Check if user already exists
            existing_user = db.query(UserModel).filter(UserModel.username == user_data.username).first()
            if existing_user:
                raise ValueError(f"User with username '{user_data.username}' already exists")
            
            # Create the user using the strategy
            user = strategy.register(db, user_data)
            
            # Convert to schema and return
            return UserSchema.from_orm(user)
    
    def authenticate(self, username: str, password: str) -> Optional[UserSchema]:
        """
        Authenticate a user using the default strategy.
        
        Args:
            username: The username to authenticate
            password: The password to verify
            
        Returns:
            The authenticated user data or None if authentication fails
        """
        # Get the appropriate strategy
        strategy_class = self.strategies[self.default_strategy]
        strategy = strategy_class()
        
        # Use context manager for database session
        with get_db() as db:
            # Authenticate the user using the strategy
            user = strategy.authenticate(db, username, password)
            
            if user:
                # Update last login time
                user.last_login = datetime.utcnow()
                db.commit()
                
                # Convert to schema and return
                return UserSchema.from_orm(user)
            
            return None
    
    def generate_auth_token(self, user: UserSchema) -> str:
        """
        Generate an authentication token for the user.
        
        Args:
            user: The user to generate a token for
            
        Returns:
            The generated token
        """
        # Generate a JWT token
        return generate_token(user.user_id, user.username)
    
    def verify_auth_token(self, token: str) -> Optional[UserSchema]:
        """
        Verify an authentication token and return the associated user.
        
        Args:
            token: The token to verify
            
        Returns:
            The user associated with the token or None if verification fails
        """
        # Extract user ID from token
        user_id = self._extract_user_id_from_token(token)
        if not user_id:
            return None
        
        # Use context manager for database session
        with get_db() as db:
            # Get the user
            user = db.query(UserModel).filter(UserModel.user_id == user_id).first()
            
            if user:
                # Convert to schema and return
                return UserSchema.from_orm(user)
            
            return None
    
    def _extract_user_id_from_token(self, token: str) -> Optional[int]:
        """
        Extract the user ID from a token.
        
        Args:
            token: The token to extract from
            
        Returns:
            The user ID or None if extraction fails
        """
        try:
            # Decode the token and extract user ID
            # This is a simplified example - in a real app, you'd verify the token signature
            from jwt import decode, InvalidTokenError
            
            # Get the secret key from environment
            import os
            secret_key = os.environ.get('JWT_SECRET', 'dev-secret-key')
            
            # Decode the token
            payload = decode(token, secret_key, algorithms=['HS256'])
            return payload.get('user_id')
        except InvalidTokenError:
            logger.warning(f"Invalid token: {token}")
            return None
        except Exception as e:
            logger.error(f"Error extracting user ID from token: {e}")
            return None
