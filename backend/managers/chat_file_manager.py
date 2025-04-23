# RAI_Chat/Backend/managers/chat_file_manager.py

import os
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy import desc, update, delete

# Import core components
from core.database.models import Session as SessionModel
from core.database.connection import get_db # To be used by calling functions

# Import path manager functions
from utils.path import DATA_DIR, get_user_chat_filepath, get_user_base_dir # Import necessary paths/functions

logger = logging.getLogger(__name__)

# Base path is now managed by path_manager.py

class ChatFileManager:
    """
    Manages chat session metadata in the database and associated transcript files
    on the filesystem for a specific user.
    """

    def __init__(self): # Removed base_data_path argument
        """
        Initializes the ChatFileManager.
        Uses DATA_DIR from path_manager for the base data path.
        """
        # Use DATA_DIR from path_manager
        self.base_data_path = DATA_DIR
        if not self.base_data_path.exists():
             try:
                 self.base_data_path.mkdir(parents=True, exist_ok=True)
                 logger.info(f"Created base data directory: {self.base_data_path}")
             except OSError as e:
                 logger.error(f"Failed to create base data directory {self.base_data_path}: {e}", exc_info=True)
                 raise # Cannot proceed without data directory

        logger.info(f"ChatFileManager initialized. Base data path: {self.base_data_path}")

    # Removed _get_user_sessions_path as it's no longer needed

    def _get_session_transcript_path(self, user_id: int, session_id: str) -> Path:
        """Gets the path to a specific session's transcript file using the new path manager function."""
        # Validate session_id
        session_id = self._validate_session_id(session_id)
        # Use the updated path manager function
        return get_user_chat_filepath(user_id, session_id)

    def _validate_session_id(self, session_id: str) -> str:
        """
        Validates session ID format and handles special cases.
        
        Args:
            session_id: The session ID to validate
        
        Returns:
            The validated (and possibly sanitized) session ID
        
        Raises:
            ValueError: If the session ID is invalid.
        """
        if not session_id:
            raise ValueError("Session ID cannot be empty")
            
        # Remove any unsafe characters (basic sanitization)
        safe_session_id = re.sub(r'[^\w\-_]', '', session_id)
        
        if safe_session_id != session_id:
            logger.warning(f"Session ID sanitized from '{session_id}' to '{safe_session_id}'")
            
        return safe_session_id

    def list_sessions(self, db: SQLAlchemySession, user_id: int) -> List[Dict[str, Any]]:
        """
        Returns a list of session metadata dictionaries for the user from the database,
        ordered by last activity descending.
        """
        logger.debug(f"Listing sessions for user_id: {user_id} from database.")
        try:
            sessions = db.query(
                SessionModel.session_id,
                SessionModel.title,
                SessionModel.created_at,
                SessionModel.last_activity_at
            ).filter(
                SessionModel.user_id == user_id
            ).order_by(
                desc(SessionModel.last_activity_at)
            ).all()

            # Convert SQLAlchemy results to list of dictionaries
            session_list = [
                {
                    "id": s.session_id,
                    "title": s.title,
                    "timestamp": s.created_at.isoformat(), # Use created_at as timestamp
                    "last_modified": s.last_activity_at.isoformat() # Use last_activity_at
                } for s in sessions
            ]
            logger.info(f"Retrieved {len(session_list)} sessions for user {user_id} from DB.")
            return session_list
        except Exception as e:
            logger.error(f"Error listing sessions for user {user_id} from DB: {e}", exc_info=True)
            return []

    def get_session_transcript(self, user_id: int, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Gets the message list (transcript) for a specific session ID from its file.
        """
        transcript_path = self._get_session_transcript_path(user_id, session_id)
        logger.debug(f"Attempting to read transcript for user {user_id}, session {session_id} from {transcript_path}")

        if not transcript_path.is_file():
            logger.warning(f"Transcript file not found: {transcript_path}")
            return None

        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)
            # Assuming the transcript file directly contains the list of messages
            if isinstance(transcript_data, list):
                logger.info(f"Successfully read transcript with {len(transcript_data)} messages from {transcript_path}")
                return transcript_data
            else:
                 logger.warning(f"Invalid transcript format (expected list) in {transcript_path}")
                 return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from transcript file {transcript_path}: {e}")
            return None
        except IOError as e:
            logger.error(f"Error reading transcript file {transcript_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading transcript file {transcript_path}: {e}", exc_info=True)
            return None

    def save_session_transcript(self, db: SQLAlchemySession, user_id: int, session_id: str, transcript_data: List[Dict[str, Any]], session_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Saves transcript data to a file and updates/creates session metadata in the database.

        Args:
            db: The database session.
            user_id: The user ID.
            session_id: The session ID.
            transcript_data: The list of messages (transcript) to save.
            session_metadata: Optional dictionary with metadata to update in DB (e.g., 'title').

        Returns:
            True if successful, False otherwise.
        """
        transcript_path = self._get_session_transcript_path(user_id, session_id)
        logger.info(f"Attempting to save transcript for user {user_id}, session {session_id} to {transcript_path}")

        # 1. Ensure directory exists
        try:
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory {transcript_path.parent}: {e}", exc_info=True)
            return False

        # 2. Save transcript file
        try:
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=4)
            logger.info(f"Transcript file saved successfully: {transcript_path}")
        except (IOError, TypeError) as e:
            logger.error(f"Error saving transcript file {transcript_path}: {e}", exc_info=True)
            return False # Don't proceed if file save fails

        # 3. Update/Insert database record
        try:
            # Prepare data for update/insert
            db_data = {
                "user_id": user_id,
                "last_activity_at": datetime.utcnow() # Always update last activity
            }
            if session_metadata:
                if 'title' in session_metadata:
                    db_data['title'] = session_metadata['title']
                # Add other metadata fields from session_metadata if needed

            # Check if session exists
            existing_session = db.query(SessionModel.session_id).filter_by(session_id=session_id, user_id=user_id).first()

            if existing_session:
                # Update existing session
                logger.debug(f"Updating existing session {session_id} in DB.")
                stmt = update(SessionModel).where(SessionModel.session_id == session_id).values(**db_data)
                db.execute(stmt)
            else:
                # Insert new session
                logger.debug(f"Inserting new session {session_id} into DB.")
                db_data['session_id'] = session_id
                db_data['user_id'] = user_id
                # Set created_at only for new sessions
                db_data['created_at'] = db_data.get('created_at', datetime.utcnow())
                if 'title' not in db_data: # Add default title if missing
                    db_data['title'] = f"Chat {session_id[:8]}"

                new_session = SessionModel(**db_data)
                db.add(new_session)

            # Commit happens in the get_db context manager
            logger.info(f"Session metadata for {session_id} saved/updated in DB.")
            return True

        except Exception as e:
            logger.error(f"Error saving session metadata to DB for session {session_id}, user {user_id}: {e}", exc_info=True)
            # Consider rolling back file save? Or log inconsistency?
            # For now, report failure.
            return False


    def create_new_session_id(self) -> str:
        """
        Creates a new unique session ID using UUID.
        
        Returns:
            A string containing a new unique session ID.
        """
        # Import here to avoid circular imports
        import uuid
        return str(uuid.uuid4())
        
    def delete_session(self, db: SQLAlchemySession, user_id: int, session_id: str) -> bool:
        """
        Deletes the session record from the database and the associated transcript file.
        Note: Does NOT delete contextual_memory.json (handled by ContextualMemoryManager).
        """
        transcript_path = self._get_session_transcript_path(user_id, session_id)
        logger.info(f"Attempting to delete session {session_id} for user {user_id} (DB record and transcript: {transcript_path})")

        deleted_db = False
        deleted_file = False
        error_occurred = False

        # 1. Delete database record
        try:
            stmt = delete(SessionModel).where(SessionModel.session_id == session_id, SessionModel.user_id == user_id)
            result = db.execute(stmt)
            if result.rowcount > 0:
                deleted_db = True
                logger.info(f"Deleted session record {session_id} from DB.")
            else:
                logger.warning(f"Session record {session_id} not found in DB for user {user_id}.")
                # Continue to delete file even if DB record wasn't found
        except Exception as e:
            logger.error(f"Error deleting session {session_id} from DB: {e}", exc_info=True)
            error_occurred = True # Mark error but try to delete file

        # 2. Delete transcript file
        try:
            if transcript_path.is_file():
                transcript_path.unlink()
                deleted_file = True
                logger.info(f"Deleted transcript file: {transcript_path}")
            else:
                logger.info(f"Transcript file not found, nothing to delete: {transcript_path}")
                # If DB record was also not found, this is fine. If DB record *was* deleted, log potential inconsistency.
                if deleted_db:
                     logger.warning(f"DB record for session {session_id} deleted, but transcript file was missing.")

        except OSError as e:
            logger.error(f"Error deleting transcript file {transcript_path}: {e}", exc_info=True)
            error_occurred = True
        except Exception as e:
             logger.error(f"Unexpected error deleting transcript file {transcript_path}: {e}", exc_info=True)
             error_occurred = True

        # Return True only if no errors occurred during DB or file deletion attempts.
        # Even if one part succeeded, an error in the other means incomplete deletion.
        return not error_occurred