# RAI_Chat/Backend/core/auth/strategies.py

import logging
import bcrypt
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import Optional

# Import database models and connection utilities
from RAI_Chat.backend.core.database.models import User as UserModel # Rename to avoid confusion
from RAI_Chat.backend.core.database.connection import get_db

# Import auth utilities and schemas
from .utils import verify_password
from .models import UserSchema # Pydantic schema for return type

logger = logging.getLogger(__name__)

class AuthStrategy:
    """Base class for authentication strategies."""
    def authenticate(self, db: SQLAlchemySession, **credentials) -> Optional[UserModel]:
        """Authenticates a user based on provided credentials."""
        raise NotImplementedError

    def get_user_info(self, db: SQLAlchemySession, identifier: str) -> Optional[UserModel]:
        """Retrieves user information based on an identifier (e.g., user_id, username, crm_id)."""
        raise NotImplementedError


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
        logger.debug(f"Attempting local authentication for username: {username}")
        if not username or not password:
            logger.warning("Authentication attempt with empty username or password.")
            return None

        try:
            user = db.query(UserModel).filter(UserModel.username == username).first()

            if not user:
                logger.warning(f"Local authentication failed: User '{username}' not found in database.") # More specific log
                return None

            if not user.hashed_password:
                logger.error(f"Local authentication error: User '{username}' exists but has no password hash set.")
                return None # Or handle as a specific error case

            if not user.is_active:
                 logger.warning(f"Local authentication failed: User '{username}' is marked as inactive.") # More specific log
                 return None

            # Verify the provided password against the stored hash
            # Log the hash format for debugging
            logger.debug(f"Stored hash format: {type(user.hashed_password)}, value: {user.hashed_password[:10]}...")
            
            # Try both with and without encoding
            if verify_password(user.hashed_password.encode('utf-8'), password):
                logger.info(f"Local authentication successful for user: {username} (ID: {user.user_id})")
                return user
            elif isinstance(user.hashed_password, str) and bcrypt.checkpw(password.encode('utf-8'), user.hashed_password.encode('utf-8')):
                logger.info(f"Local authentication successful (direct check) for user: {username} (ID: {user.user_id})")
                return user
            else:
                logger.warning(f"Local authentication failed: Password verification failed for user '{username}'.") # More specific log
                return None

        except Exception as e:
            logger.error(f"Error during local authentication for user '{username}': {e}", exc_info=True)
            return None # Return None on unexpected errors

    def get_user_info(self, db: SQLAlchemySession, username: str) -> Optional[UserModel]:
        """Retrieves user information by username from the local DB."""
        logger.debug(f"Retrieving local user info for username: {username}")
        try:
            user = db.query(UserModel).filter(UserModel.username == username).first()
            return user
        except Exception as e:
            logger.error(f"Error retrieving local user info for '{username}': {e}", exc_info=True)
            return None


class CRMStrategy(AuthStrategy):
    """
    Placeholder for CRM authentication strategy.
    Actual implementation will depend on the specific CRM API and auth flow (OAuth, SAML, API Key).
    """
    def authenticate(self, db: SQLAlchemySession, **credentials) -> Optional[UserModel]:
        logger.warning("CRM authentication strategy not yet implemented.")
        # Example: Might take an access_token, validate it with CRM, get CRM user ID,
        # then find or create a linked local user.
        # crm_token = credentials.get("crm_token")
        # if not crm_token: return None
        # crm_user_data = self._validate_crm_token_and_get_user(crm_token)
        # if not crm_user_data: return None
        # crm_id = crm_user_data.get("id")
        # user = db.query(UserModel).filter(UserModel.crm_user_id == crm_id, UserModel.auth_provider == 'crm_name').first()
        # if not user:
        #     # Optionally create a local user linked to the CRM ID
        #     user = self._create_linked_crm_user(db, crm_user_data)
        # return user
        return None

    def get_user_info(self, db: SQLAlchemySession, identifier: str) -> Optional[UserModel]:
        logger.warning("CRM get_user_info strategy not yet implemented.")
        # Might look up user by crm_user_id
        # user = db.query(UserModel).filter(UserModel.crm_user_id == identifier, UserModel.auth_provider == 'crm_name').first()
        # return user
        return None

    # Placeholder helper methods for CRM interaction
    # def _validate_crm_token_and_get_user(self, token): raise NotImplementedError
    # def _create_linked_crm_user(self, db, crm_data): raise NotImplementedError