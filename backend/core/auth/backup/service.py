# RAI_Chat/Backend/core/auth/service.py

import logging
from datetime import datetime
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import Optional, Dict, Type

# Import core components
from RAI_Chat.backend.core.database.models import User as UserModel
from RAI_Chat.backend.core.database.connection import get_db # Context manager for sessions
from .strategies import AuthStrategy, LocalStrategy, CRMStrategy # Import strategies
from .models import UserSchema, UserCreateSchema # Pydantic Schemas
from .utils import hash_password, verify_password, generate_token # Auth utilities

logger = logging.getLogger(__name__)

class AuthService:
    """
    Service layer for handling user authentication and management.
    Orchestrates the use of different authentication strategies.
    """

    def __init__(self, strategies: Optional[Dict[str, Type[AuthStrategy]]] = None):
        """
        Initializes the AuthService.

        Args:
            strategies: A dictionary mapping strategy names (e.g., 'local', 'crm_name')
                        to their corresponding strategy classes. If None, defaults to LocalStrategy.
        """
        if strategies is None:
            self.strategies: Dict[str, Type[AuthStrategy]] = {
                'local': LocalStrategy
                # Add CRMStrategy instance here when implemented and configured
                # 'my_crm': CRMStrategy(...)
            }
        else:
            self.strategies = strategies
        logger.info(f"AuthService initialized with strategies: {list(self.strategies.keys())}")

    def _get_strategy(self, provider: str = 'local') -> Optional[AuthStrategy]:
        """Retrieves the strategy instance for the given provider."""
        strategy_class = self.strategies.get(provider)
        if strategy_class:
            return strategy_class() # Instantiate the strategy
        logger.error(f"Authentication strategy for provider '{provider}' not found.")
        return None

    def authenticate(self, db: SQLAlchemySession, provider: str = 'local', **credentials) -> Optional[UserModel]:
        """
        Authenticates a user using the specified provider and credentials.

        Args:
            db: The database session.
            provider: The authentication provider name (e.g., 'local', 'crm_name').
            **credentials: Credentials required by the strategy (e.g., username, password for local).

        Returns:
            The authenticated UserModel object if successful, None otherwise.
        """
        strategy = self._get_strategy(provider)
        if not strategy:
            return None

        try:
            user = strategy.authenticate(db=db, **credentials)
            if user and user.is_active:
                # Update last_login_at on successful authentication
                user.last_login_at = datetime.utcnow()
                db.add(user)
                db.commit() # Commit the last login time update
                db.refresh(user)
                logger.info(f"User {user.username} (ID: {user.user_id}) authenticated successfully via {provider}.")
                return user
            elif user and not user.is_active:
                 logger.warning(f"Authentication failed for user {credentials.get('username', 'N/A')}: Account inactive.")
                 return None
            else:
                 # Strategy returned None (auth failed)
                 logger.warning(f"Authentication failed via {provider} for user {credentials.get('username', 'N/A')}.")
                 return None
        except Exception as e:
            logger.error(f"Exception during authentication via {provider}: {e}", exc_info=True)
            db.rollback() # Rollback any potential partial changes
            return None

    def get_user_by_id(self, db: SQLAlchemySession, user_id: int) -> Optional[UserModel]:
        """Retrieves a user by their unique ID."""
        logger.debug(f"Attempting to retrieve user by ID: {user_id}")
        try:
            user = db.query(UserModel).filter(UserModel.user_id == user_id).first()
            if not user:
                 logger.debug(f"User with ID {user_id} not found.")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by ID {user_id}: {e}", exc_info=True)
            return None

    def get_user_by_username(self, db: SQLAlchemySession, username: str) -> Optional[UserModel]:
        """Retrieves a user by their username (primarily for local auth checks)."""
        logger.debug(f"Attempting to retrieve user by username: {username}")
        try:
            user = db.query(UserModel).filter(UserModel.username == username).first()
            if not user:
                 logger.debug(f"User with username '{username}' not found.")
            return user
        except Exception as e:
            logger.error(f"Error retrieving user by username '{username}': {e}", exc_info=True)
            return None

    def login(self, db: SQLAlchemySession, username: str, password: str) -> dict:
        """
        Authenticates a user and generates a JWT token if successful.

        Args:
            db: The database session
            username: User's username
            password: User's password

        Returns:
            dict: Response containing token, user_id, and status
        """
        user = self.authenticate(db, provider='local', username=username, password=password)
        
        if not user:
            logger.warning(f"Login failed for user {username}")
            return {
                'status': 'error',
                'error': 'Invalid username or password'
            }
            
        # Generate JWT token using the utility function
        token = generate_token(user.user_id, user.username)
        
        logger.info(f"Login successful for user {username} (ID: {user.user_id})")
        return {
            'status': 'success',
            'token': token,
            'user_id': user.user_id,
            'username': user.username
        }
    
    def register(self, db: SQLAlchemySession, username: str, password: str, email: str = None) -> dict:
        """
        Registers a new user and generates a JWT token.
        
        Args:
            db: The database session
            username: Desired username
            password: Desired password
            email: Optional email address
            
        Returns:
            dict: Response containing token, user_id, and status
        """
        # Create user data schema
        user_data = UserCreateSchema(
            username=username,
            password=password,
            email=email or ""
        )
        
        # Create the user
        user = self.create_local_user(db, user_data)
        
        if not user:
            return {
                'status': 'error',
                'error': 'Username already exists or invalid data'
            }
        
        # Generate JWT token
        token = generate_token(user.user_id, user.username)
        
        return {
            'status': 'success',
            'token': token,
            'user_id': user.user_id,
            'username': user.username
        }

    def create_local_user(self, db: SQLAlchemySession, user_data: UserCreateSchema) -> Optional[UserModel]:
        """
        Creates a new local user in the database.

        Args:
            db: The database session.
            user_data: Pydantic schema containing user creation details (username, password, email).

        Returns:
            The created UserModel object if successful, None otherwise (e.g., username exists).
        """
        logger.info(f"Attempting to create local user: {user_data.username}")
        # Check if username already exists
        existing_user = self.get_user_by_username(db, user_data.username)
        if existing_user:
            logger.warning(f"Cannot create user: Username '{user_data.username}' already exists.")
            return None

        try:
            hashed_pw = hash_password(user_data.password)
            new_user = UserModel(
                username=user_data.username,
                hashed_password=hashed_pw.decode('utf-8'), # Store hash as string
                email=user_data.email,
                auth_provider='local', # Explicitly set for local users
                is_active=True, # Default new users to active
                created_at=datetime.utcnow()
            )
            db.add(new_user)
            db.commit() # Commit the new user
            db.refresh(new_user) # Refresh to get the auto-generated user_id
            logger.info(f"Successfully created local user '{new_user.username}' with ID: {new_user.user_id}")
            return new_user
        except Exception as e:
            logger.error(f"Error creating local user '{user_data.username}': {e}", exc_info=True)
            db.rollback() # Rollback on error
            return None

# Example instantiation (could be done in main app setup or via dependency injection)
# auth_service = AuthService()

# Example usage (e.g., in an API endpoint)
# with get_db() as db_session:
#     user = auth_service.authenticate(db_session, provider='local', username='testuser', password='password123')
#     if user:
#         user_schema = UserSchema.from_orm(user)
#         print(f"Authenticated user: {user_schema.dict()}")