# RAI_Chat/Backend/core/auth/strategies.py
# Docker-specific version with relative imports

import logging
import bcrypt
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import Optional

# Import database models and connection utilities using relative imports
from ..database.models import User as UserModel
from ..database.connection import get_db

# Import auth utilities and schemas
from .utils import verify_password
from .models import UserSchema # Pydantic schema for return type

logger = logging.getLogger(__name__)

class AuthStrategy:
    """Base class for authentication strategies."""
    def authenticate(self, db: SQLAlchemySession, **credentials) -> Optional[UserModel]:
        """Authenticates a user based on provided credentials."""
        raise NotImplementedError("Subclasses must implement authenticate()")
    
    def register(self, db: SQLAlchemySession, **user_data) -> Optional[UserModel]:
        """Registers a new user with the provided data."""
        raise NotImplementedError("Subclasses must implement register()")

class LocalStrategy(AuthStrategy):
    """Handles authentication against the local user database."""
    
    def authenticate(self, db: SQLAlchemySession, username: str, password: str) -> Optional[UserModel]:
        """
        Authenticates a user using username and password against the local DB.
        
        Args:
            db: The database session.
            username: The username provided by the user.
            password: The password provided by the user.
            
        Returns:
            The authenticated UserModel object if successful, None otherwise.
        """
        try:
            # Get the user from the database
            user = self.get_user_info(db, username)
            
            if not user:
                logger.warning(f"Authentication failed: User '{username}' not found")
                return None
            
            # Verify the password
            if not user.hashed_password:
                logger.warning(f"Authentication failed: User '{username}' has no password set")
                return None
            
            # Check if the password matches
            if verify_password(password, user.hashed_password):
                logger.info(f"Authentication successful for user: {username}")
                return user
            else:
                logger.warning(f"Authentication failed: Invalid password for user '{username}'")
                return None
        except Exception as e:
            logger.error(f"Error during local authentication: {str(e)}")
            return None
    
    def get_user_info(self, db: SQLAlchemySession, username: str) -> Optional[UserModel]:
        """Retrieves user information by username from the local DB."""
        try:
            # Query the database for the user
            return db.query(UserModel).filter(UserModel.username == username).first()
        except Exception as e:
            logger.error(f"Error retrieving user info: {str(e)}")
            return None
    
    def register(self, db: SQLAlchemySession, user_data) -> UserModel:
        """
        Registers a new user in the local database.
        
        Args:
            db: The database session.
            user_data: The user data for registration.
            
        Returns:
            The created UserModel object.
            
        Raises:
            ValueError: If registration fails.
        """
        try:
            # Import the password hashing utility
            from .utils import hash_password
            
            # Create a new user with simplified model
            new_user = UserModel(
                username=user_data.username,
                hashed_password=hash_password(user_data.password)
            )
            
            # Add to database and commit
            db.add(new_user)
            db.commit()
            
            logger.info(f"Successfully registered new user: {user_data.username}")
            return new_user
        except Exception as e:
            # Rollback on error
            db.rollback()
            logger.error(f"Error during user registration: {str(e)}")
            raise ValueError(f"User registration failed: {str(e)}")

class CRMStrategy(AuthStrategy):
    """
    Placeholder for CRM authentication strategy.
    Actual implementation will depend on the specific CRM API and auth flow (OAuth, SAML, API Key).
    """
    
    def authenticate(self, db: SQLAlchemySession, **credentials) -> Optional[UserModel]:
        """
        Authenticates a user against the CRM system.
        
        Args:
            db: The database session.
            **credentials: The credentials for CRM authentication.
            
        Returns:
            The authenticated UserModel object if successful, None otherwise.
        """
        # This is a placeholder implementation
        logger.warning("CRM authentication not yet implemented")
        return None
    
    def get_user_info(self, db: SQLAlchemySession, identifier: str) -> Optional[UserModel]:
        """
        Retrieves user information from the CRM system.
        
        Args:
            db: The database session.
            identifier: The user identifier in the CRM system.
            
        Returns:
            The UserModel object if found, None otherwise.
        """
        # This is a placeholder implementation
        logger.warning("CRM user info retrieval not yet implemented")
        return None
    
    def register(self, db: SQLAlchemySession, user_data) -> UserModel:
        """
        Registers a new user with the CRM system.
        
        Args:
            db: The database session.
            user_data: The user data for registration.
            
        Returns:
            The created UserModel object.
            
        Raises:
            ValueError: If registration fails.
        """
        # This is a placeholder implementation
        logger.warning("CRM user registration not yet implemented")
        raise ValueError("CRM user registration not yet implemented")
