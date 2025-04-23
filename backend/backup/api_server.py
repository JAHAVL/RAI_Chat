# RAI_Chat/backend/api_server.py

import os
import sys # Ensure sys is imported early
import time
import re  # Required for regex pattern matching
from pathlib import Path # Use pathlib for path manipulation

# --- Add project root to sys.path ---
# This ensures imports like 'from RAI_Chat...' work when the script is run directly or as a subprocess
try:
    # Assumes this script is in RAI_Chat/backend/
    PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    print(f"api_server.py: Added project root to sys.path: {PROJECT_ROOT}") # Use print for startup visibility
except Exception as e:
     print(f"api_server.py: Error adding project root to sys.path: {e}")
     # Exit if we can't set the path, as imports will likely fail
     sys.exit("Failed to configure sys.path")
# --- End sys.path modification ---

import json # Moved down
import logging # Moved down
import logging.handlers # Moved down
print(f"DEBUG sys.path: {sys.path}") # Add this line to check Python's search path
from datetime import datetime, timedelta, timezone # Added timezone import
import jwt
from functools import wraps
from flask import Flask, request, jsonify, g, Response # Added Response
from flask_cors import CORS # Import CORS
from pathlib import Path # Use pathlib
from sqlalchemy.orm import Session as SQLAlchemySession # For type hinting DB session

# Project setup (like adding to sys.path) is assumed to be handled by the launching script (e.g., start_all.py)
# Import necessary paths from the centralized manager
# Fix the import path to use relative import
from utils.path_manager import LOGS_DIR # Import LOGS_DIR

# --- Load Environment Variables ---
# Load early, before other imports might need them
from dotenv import load_dotenv
# Load .env from the Backend directory where this script resides
dotenv_path = Path(__file__).resolve().parent / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}") # Use print for early feedback
else:
    print(f"Warning: .env file not found at {dotenv_path}")
# --- End Load Environment Variables ---


# --- Logging Configuration ---
# Configure logging AFTER loading .env potentially
log_dir = LOGS_DIR # Use imported LOGS_DIR from path_manager
os.makedirs(log_dir, exist_ok=True)
log_file = log_dir / 'rai_api_server.log'

# Configure root logger first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a', encoding='utf-8'), # Append mode
        logging.StreamHandler(sys.stdout) # Keep console output
    ],
    force=True # Force reconfiguration
)
logger = logging.getLogger(__name__) # Get logger for this module
# --- End Logging Configuration ---


# --- Import Core Components & Managers (Docker-compatible paths) ---
try:
    # Import with paths relative to /app (Docker PYTHONPATH)
    from core.database.connection import get_db, test_db_connection # Keep get_db for other endpoints
    from core.auth.service import AuthService
    from core.auth.models import UserCreateSchema, UserLoginSchema, UserSchema
    from managers.user_session_manager import UserSessionManager
    # ConversationManager is now obtained via UserSessionManager
    # from managers.conversation_manager import ConversationManager
    # Other managers are also obtained via UserSessionManager
    # from managers.chat_file_manager import ChatFileManager
    # from managers.memory.contextual_memory import ContextualMemoryManager
    # from managers.memory.episodic_memory import EpisodicMemoryManager

    # Import our centralized LLM API interface
    from api.llm_engine.llm_api_interface import get_llm_api
    from utils.path import get_user_base_dir # Needed for filesystem listing
except ImportError as e:
     logger.critical(f"Failed to import core components or managers: {e}. Ensure PYTHONPATH is correct and modules exist.", exc_info=True)
     sys.exit(f"Import Error: {e}")
# --- End Imports ---


# --- Flask App Initialization ---
app = Flask(__name__)
# Enable CORS for all routes, allowing requests from the frontend origin
# TODO: Restrict origin in production for security
CORS(app, resources={r"/api/*": {"origins": "*"}}) # Allow all origins for now

# Load configuration (e.g., SECRET_KEY)
# IMPORTANT: Use environment variables for secrets in production!
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key-replace-me-in-prod')
if app.config['SECRET_KEY'] == 'fallback-secret-key-replace-me-in-prod':
    logger.warning("Using fallback SECRET_KEY - not secure for production!")

# Enable development mode auto-authentication
# This allows API requests without a valid token during development
app.config['DEV_AUTO_AUTH'] = os.environ.get('DEV_AUTO_AUTH', 'True').lower() in ('true', '1', 't')
if app.config['DEV_AUTO_AUTH']:
    logger.warning("DEV_AUTO_AUTH is enabled - API endpoints will auto-authenticate in development mode")
# --- End Flask App Initialization ---


# --- Service Initialization ---
# Instantiate core services - these can be singletons for the app lifetime
try:
    auth_service = AuthService() # Uses default strategies ('local')
    # Pass the base data path from config or use default
    # TODO: Load base_data_path from config/env if needed
    user_session_manager = UserSessionManager()
    logger.info("AuthService and UserSessionManager initialized.")
except Exception as e:
    logger.critical(f"Failed to initialize core services: {e}", exc_info=True)
    sys.exit("Service Initialization Error")
# --- End Service Initialization ---


# --- Database Check ---
# Optional: Test DB connection on startup
# with app.app_context(): # Need app context for get_db potentially if it uses Flask context
#     logger.info("Testing database connection...")
#     if not test_db_connection():
#          logger.critical("Database connection failed on startup. Exiting.")
#          # sys.exit("Database Connection Error") # Decide if exit is desired
#     else:
#          logger.info("Database connection test successful.")
# --- End Database Check ---


# Import the centralized authentication utilities
from core.auth.utils import token_required, generate_token


# === Authentication Endpoints (Refactored) ===

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Registers a new user using AuthService."""
    try:
        # Validate input using Pydantic schema
        user_data = UserCreateSchema(**request.json)
    except Exception as e: # Catches Pydantic validation errors
        logger.warning(f"Registration validation failed: {e}")
        return jsonify({"error": "Invalid registration data", "details": str(e)}), 400

    try:
        with get_db() as db:
            created_user = auth_service.create_local_user(db, user_data)
            
            if created_user:
                # Access user attributes while the session is still open
                username = created_user.username
                user_id = created_user.user_id
                # Create user_info schema from the model while session is open
                user_info = UserSchema.from_orm(created_user)
                
                logger.info(f"User '{username}' registered successfully (ID: {user_id}).")
                # Return user info (excluding password) upon successful registration
                return jsonify({"message": "Registration successful", "user": user_info.dict()}), 201
            else:
                # Check if username exists (AuthService handles this check now)
                logger.warning(f"Registration failed for username '{user_data.username}' (likely already exists).")
                return jsonify({"error": f"Username '{user_data.username}' may already exist or registration failed."}), 409 # Conflict or Bad Request

    except Exception as e:
        logger.error(f"Error during registration for '{user_data.username}': {e}", exc_info=True)
        return jsonify({"error": "Registration failed due to an internal server error"}), 500


@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """Logs in a user using AuthService and returns a JWT."""
    try:
        login_data = UserLoginSchema(**request.json)
    except Exception as e: # Catches Pydantic validation errors
        logger.warning(f"Login validation failed: {e}")
        return jsonify({"error": "Invalid login data", "details": str(e)}), 400

    try:
        with get_db() as db:
            # Use AuthService to authenticate
            authenticated_user = auth_service.authenticate(
                db,
                provider='local', # Specify local strategy
                username=login_data.username,
                password=login_data.password
            )

            if not authenticated_user:
                logger.warning(f"Login attempt failed for user: {login_data.username}")
                return jsonify({"error": "Invalid username or password"}), 401 # Unauthorized

            # Store user details while session is still open
            user_id = authenticated_user.user_id
            username = authenticated_user.username
            
            # Create user_info schema from the model while session is open
            user_info = UserSchema.from_orm(authenticated_user)

            # User authenticated, generate JWT using our centralized function
            token = generate_token(user_id=user_id, username=username)

            logger.info(f"User '{username}' logged in successfully.")
            return jsonify({"access_token": token, "user": user_info.dict()}), 200

    except Exception as e:
        logger.error(f"Error during login for '{login_data.username}': {e}", exc_info=True)
        return jsonify({"error": "Login failed due to an internal server error"}), 500

# === End Authentication Endpoints ===


# === API Routes (Refactored) ===

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    llm_status = "unknown"
    db_status = "unknown"
    try:
        # Check DB
        with get_db() as db: # Test getting a session
             # Use text() for literal SQL if needed, or just query metadata
             from sqlalchemy import text
             db.execute(text("SELECT 1")) # Simple query
             db_status = "ok"
    except Exception as e:
        logger.error(f"Error checking DB health: {e}")
        db_status = "error"

    try:
        # Check LLM
        llm_api = get_llm_api()
        if hasattr(llm_api, 'health_check'):
             health = llm_api.health_check()
             if health and health.get('status') == 'ok':
                 llm_status = "available"
             else:
                 llm_status = "unavailable"
        else:
             llm_status = "check_not_implemented"
    except Exception as e:
        logger.error(f"Error checking LLM health: {e}")
        llm_status = "error"

    return jsonify({
        "status": "ok" if db_status == "ok" else "error",
        "service": "rai-chat-api",
        "database_status": db_status,
        "llm_status": llm_status,
    })


@app.route('/api/chat', methods=['POST'])
@token_required
def chat():
    """Chat endpoint using refactored managers, supporting both streaming and non-streaming responses."""
    # Get authenticated user from the 'g' object set by token_required decorator
    user_id = g.current_user.user_id
    logger.info(f"--- Entered /api/chat endpoint for user {user_id} ---")
    data = request.json
    logger.debug(f"--- Received /api/chat request data: {json.dumps(data)} ---")

    session_id_from_request = data.get('session_id')
    user_message_content = data.get('message', '')
    # Check if client wants streaming (default to False for direct API calls)
    streaming_requested = data.get('streaming', False)

    if not user_message_content:
        # Cannot stream an error easily before processing starts, return standard JSON error
        return jsonify({"error": "Message content is required"}), 400

    # Non-streaming response handler (for direct API calls)
    if not streaming_requested:
        actual_session_id = None
        conversation_manager = None
        try:
            # Use get_db() context manager to obtain a database session
            with get_db() as db:
                logger.info(f"Processing non-streaming request for user {user_id}, session_req: {session_id_from_request}")
                # Get the user-specific ConversationManager instance for this chat session
                actual_session_id, conversation_manager = user_session_manager.get_conversation_manager(
                    user_id, session_id_from_request
                )

                if not conversation_manager or not actual_session_id:
                    logger.error(f"Failed to get or create ConversationManager for user {user_id}")
                    return jsonify({
                        "status": "error",
                        "error": "Could not obtain conversation manager.",
                        "session_id": session_id_from_request or "error_session"
                    }), 500

                logger.info(f"Got ConversationManager. Actual session ID: {actual_session_id}. Processing message.")

                # Get the response generator from ConversationManager
                response_generator = conversation_manager.get_response(db, user_message_content)

                # Collect all chunks
                final_response_data = None
                for chunk in response_generator:
                    # Keep track of the last (final) chunk
                    final_response_data = chunk
                
                # If we have a final response, return it
                if final_response_data:
                    # Add session_id to the response
                    final_response_data['session_id'] = actual_session_id
                    
                    # Save chat after response generation
                    if final_response_data.get('status') != 'error':
                        try:
                            logger.info(f"Saving session {actual_session_id}")
                            conversation_manager.save_current_chat(db=db)
                        except Exception as save_e:
                            logger.error(f"Error saving session {actual_session_id}: {save_e}", exc_info=True)
                    
                    return jsonify(final_response_data)
                else:
                    # No response generated
                    return jsonify({
                        "status": "error",
                        "error": "No response generated",
                        "session_id": actual_session_id
                    }), 500

        except Exception as e:
            logger.exception(f"Exception in /api/chat non-streaming for user {user_id}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "response": "I encountered an internal error. Please try again.",
                "session_id": actual_session_id or session_id_from_request or "error_session"
            }), 500

    # Streaming response handler (original implementation)
    def stream_response():
        actual_session_id = None # Initialize
        conversation_manager = None # Initialize
        try:
            # Use get_db() context manager to obtain a database session
            with get_db() as db:
                logger.info(f"Attempting to get ConversationManager for user {user_id}, session_req: {session_id_from_request}")
                # Get the user-specific ConversationManager instance for this chat session
                actual_session_id, conversation_manager = user_session_manager.get_conversation_manager(
                    user_id, session_id_from_request
                )

                if not conversation_manager or not actual_session_id:
                     logger.error(f"Failed to get or create ConversationManager for user {user_id}")
                     raise RuntimeError("Could not obtain conversation manager.")

                logger.info(f"Got ConversationManager. Actual session ID: {actual_session_id}. CM instance: {conversation_manager}")
                logger.info(f"Attempting to get response generator from ConversationManager for message: '{user_message_content[:50]}...'")

                # Get the response generator from ConversationManager
                response_generator = conversation_manager.get_response(db, user_message_content)

                # Iterate through the generator, yielding each chunk
                final_response_data = None
                for chunk in response_generator:
                    logger.info(f"--- Yielding chunk: {str(chunk)[:100]}... ---")
                    # Add session_id to the chunk before yielding
                    chunk_to_yield = chunk.copy() # Avoid modifying original chunk if reused
                    chunk_to_yield['session_id'] = actual_session_id
                    yield json.dumps(chunk_to_yield) + '\n'
                    final_response_data = chunk # Keep track of the last (final) chunk

                logger.info(f"--- Finished yielding chunks. Final chunk: {str(final_response_data)[:100]}... ---")

                # --- Save chat after response generation (if successful and CM exists) ---
                # Check the status of the *final* response chunk
                if final_response_data and final_response_data.get('status') != 'error' and conversation_manager:
                    try:
                        logger.info(f"--- Attempting to save session {actual_session_id} via CM.save_current_chat ---")
                        save_success = conversation_manager.save_current_chat(db=db) # Pass db session
                        if save_success:
                             logger.info(f"--- Finished CM.save_current_chat successfully for session {actual_session_id} ---")
                        else:
                             logger.error(f"--- CM.save_current_chat reported failure for session {actual_session_id} ---")
                    except Exception as save_e:
                        logger.error(f"Error triggering save for session {actual_session_id} after response: {save_e}", exc_info=True)

        except Exception as e:
            logger.exception(f"!!! EXCEPTION in /api/chat stream for user {user_id} !!!")
            # Yield a final error chunk if something goes wrong during streaming
            error_response = {
                "response": "I encountered an internal error. Please try again.",
                "session_id": actual_session_id or session_id_from_request or "error_session",
                "status": "error"
            }
            yield json.dumps(error_response) + '\n'

    # Return a streaming response if streaming was requested
    # Use mimetype 'application/x-ndjson' for newline-delimited JSON
    return Response(stream_response(), mimetype='application/x-ndjson')


@app.route('/api/memory', methods=['GET'])
@token_required
def get_memory():
    """Get memory contents (user remembered facts) for the authenticated user."""
    user: UserSchema = g.current_user
    user_id = user.user_id
    logger.info(f"Memory request received for user: {user_id}")
    try:
        # Get managers via UserSessionManager
        managers = user_session_manager.get_user_managers(user_id)
        cmm = managers['cmm'] # Get user-specific ContextualMemoryManager
        user_facts = cmm.user_remembered_facts # Access refactored attribute

        return jsonify({
           "user_profile_facts": user_facts,
           "status": "success"
        })
    except Exception as e:
        logger.error(f"Error retrieving memory for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve memory", "status": "error"}), 500


@app.route('/api/sessions', methods=['GET'])
@token_required # <-- Re-enabled
def list_sessions():
    """List saved sessions for the authenticated user by scanning the filesystem."""
    user: UserSchema = g.current_user # Get authenticated user schema from decorator
    user_id = user.user_id # Use the actual user ID from the token
    logger.info(f"List sessions request received for user: {user_id} (Filesystem Scan)")
    saved_sessions = []
    try:
        user_data_dir = get_user_base_dir(user_id)
        logger.debug(f"Scanning user data directory: {user_data_dir}")

        if not user_data_dir.is_dir():
            logger.warning(f"User data directory not found: {user_data_dir}")
            return jsonify({"sessions": [], "count": 0, "status": "success"})

        # Iterate through items in the user's data directory
        for item in user_data_dir.iterdir():
            if item.is_dir():
                session_id = item.name
                context_file = item / "context.json"
                transcript_file = item / "transcript.json" # Check for transcript as well

                # Consider it a session if context or transcript exists
                if context_file.is_file() or transcript_file.is_file():
                    logger.debug(f"Found potential session directory: {session_id}")
                    title = f"Chat {session_id[:8]}..." # Default title
                    last_modified_ts = 0.0
                    created_ts = 0.0

                    # Use the most recently modified file (context or transcript) for timestamp
                    target_file_for_meta = None
                    if context_file.is_file():
                        target_file_for_meta = context_file
                    if transcript_file.is_file():
                         # If transcript is newer or context doesn't exist, use transcript
                         if target_file_for_meta is None or transcript_file.stat().st_mtime > target_file_for_meta.stat().st_mtime:
                              target_file_for_meta = transcript_file

                    if target_file_for_meta:
                         try:
                              file_stat = target_file_for_meta.stat()
                              last_modified_ts = file_stat.st_mtime
                              # Use modification time also for creation time as a fallback
                              created_ts = file_stat.st_mtime
                              # Try reading context file for a better title
                              if context_file.is_file():
                                   with open(context_file, 'r', encoding='utf-8') as f:
                                        context_data = json.load(f)
                                        messages = context_data.get("messages", [])
                                        for turn in messages:
                                             if turn.get("user_input"):
                                                  user_input = turn["user_input"]
                                                  title = user_input[:30] + "..." if len(user_input) > 30 else user_input
                                                  break # Use first user message
                         except json.JSONDecodeError:
                              logger.warning(f"Could not decode JSON from {context_file} for title.")
                         except Exception as e:
                              logger.error(f"Error processing session {session_id} metadata from {target_file_for_meta}: {e}")

                    # Convert timestamps to ISO format UTC
                    # Ensure datetime and timezone are imported: from datetime import datetime, timezone
                    last_modified_iso = datetime.fromtimestamp(last_modified_ts, tz=timezone.utc).isoformat()
                    created_iso = datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat()

                    saved_sessions.append({
                        "id": session_id,
                        "title": title,
                        "timestamp": created_iso, # Using modification time as creation
                        "last_modified": last_modified_iso
                    })

        # Sort by last modified time descending
        saved_sessions.sort(key=lambda s: s["last_modified"], reverse=True)

        logger.info(f"Found {len(saved_sessions)} sessions for user {user_id} via filesystem scan.")
        # ADDED DEBUG LOG: Check type and content before returning
        logger.debug(f"Returning sessions: type={type(saved_sessions)}, content={saved_sessions}")
        return jsonify({
            "sessions": saved_sessions,
            "count": len(saved_sessions),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error listing saved sessions for user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to list saved sessions", "status": "error"}), 500


@app.route('/api/sessions/<string:session_id>', methods=['DELETE'])
@token_required
def delete_session(session_id):
    """Delete a session (DB record, transcript file, context file, memory index)."""
    user: UserSchema = g.current_user
    user_id = user.user_id
    logger.info(f"Received request from user {user_id} to delete session: {session_id}")

    try:
        # Get managers via UserSessionManager
        managers = user_session_manager.get_user_managers(user_id)
        chat_file_manager = managers['cfm']
        episodic_mem = managers['episodic']
        cmm = managers['cmm']

        # Use a single DB transaction for all deletions
        with get_db() as db:
            # 1. Delete DB record and transcript file via ChatFileManager
            db_transcript_deleted = chat_file_manager.delete_session(db, user_id, session_id)

            # 2. Delete context file via ContextualMemoryManager
            context_deleted = cmm.reset_session_context(session_id) # reset also deletes file

            # 3. Delete episodic memory index entry
            episodic_index_reset = episodic_mem.reset_session_in_memory(session_id)
            # Optionally delete archived episodic files too?
            # episodic_files_deleted = episodic_mem.delete_session_archive(session_id)

        # 4. Remove from active ConversationManager cache if it exists
        deleted_active = False
        if user_id in user_session_manager._user_managers_cache:
             session_cache = user_session_manager._user_managers_cache[user_id].get("chat_sessions", {})
             if session_id in session_cache:
                  del session_cache[session_id]
                  deleted_active = True
                  logger.info(f"Removed session {session_id} from active sessions cache.")

        # Determine overall success
        # Consider successful if DB/transcript deleted AND context deleted
        # Episodic index reset is less critical for basic operation
        if db_transcript_deleted and context_deleted:
            message = f"Successfully deleted session {session_id}."
            if deleted_active: message += " Also removed from active cache."
            logger.info(message)
            return jsonify({"message": message, "status": "success"})
        else:
            # Log specifics about what failed
            error_msg = f"Failed to fully delete session {session_id}: "
            details = []
            if not db_transcript_deleted: details.append("DB record/transcript deletion failed")
            if not context_deleted: details.append("Context file deletion failed")
            error_msg += "; ".join(details)
            logger.error(error_msg)
            return jsonify({"error": error_msg, "status": "error"}), 500 # Internal error as deletion failed partially

    except Exception as e:
        logger.error(f"Error processing delete request for user {user_id}, session {session_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete session due to an internal server error", "status": "error"}), 500


@app.route('/api/sessions/<string:session_id>/history', methods=['GET'])
@token_required
def get_session_history(session_id):
    """Get message history (transcript) for a specific saved session."""
    user: UserSchema = g.current_user
    user_id = user.user_id
    logger.info(f"Get history request received for user {user_id}, session {session_id}")
    
    # Get the proper data directory path
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    
    # SPECIAL DEBUG FOR SPECIFIC SESSION
    if session_id == "654a3a1f-4392-47ff-97f8-3f75358a6973":
        logger.info("=== DEBUGGING SPECIFIC SESSION ===")
        transcript_path = os.path.join(data_dir, str(user_id), session_id, "transcript.json")
        logger.info(f"Direct checking transcript path: {transcript_path}")
        logger.info(f"File exists: {os.path.exists(transcript_path)}")
        
        # Manually read and parse the file
        try:
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                    logger.info(f"Raw transcript data (first turn): {json.dumps(transcript_data[0]) if transcript_data else 'No data'}")
                    
                    # Manually transform to frontend format for debugging
                    frontend_messages = []
                    processed_user_inputs = set()  # Track user inputs to avoid duplicates
                    
                    # First pass: Force include the first user message regardless of duplicates
                    if transcript_data and 'user_input' in transcript_data[0]:
                        first_user_message = {
                            'id': f"user-{transcript_data[0].get('turn_id', 'unknown')}",
                            'role': 'user',
                            'content': transcript_data[0].get('user_input', ''),
                            'timestamp': transcript_data[0].get('timestamp'),
                            'sequenceOrder': 0  # Ensure it comes first
                        }
                        frontend_messages.append(first_user_message)
                        processed_user_inputs.add(transcript_data[0].get('user_input', ''))
                        logger.info(f"DEBUG: Added first user message: {transcript_data[0].get('user_input', '')[:30]}...")
                    
                    # First pass: collect all turns in chronological order to preserve the sequence
                    # and identify which user prompts come first
                    user_prompt_order = {}  # To track the first occurrence of each user prompt
                    
                    for i, turn in enumerate(transcript_data):
                        if 'user_input' in turn:
                            user_input = turn.get('user_input', '')
                            # Only track the first occurrence of each unique user input
                            if user_input not in user_prompt_order:
                                user_prompt_order[user_input] = i
                    
                    # Second pass: process turns in order but respect the first occurrence of user messages
                    for i, turn in enumerate(transcript_data):
                        # Process search signals in LLM response
                        if 'llm_output' in turn and 'llm_response' in turn['llm_output'] and 'response_tiers' in turn['llm_output']['llm_response']:
                            tier3_content = turn['llm_output']['llm_response']['response_tiers'].get('tier3', '')
                            
                            # Check for search signals like [SEARCH: query]
                            if tier3_content and '[SEARCH:' in tier3_content:
                                # Extract the search query
                                search_match = re.search(r'\[SEARCH:\s*([^\]]+)\]', tier3_content)
                                if search_match:
                                    search_query = search_match.group(1).strip()
                                    # Add a system message for the search instead of showing the raw [SEARCH: ...] text
                                    system_message = {
                                        'id': f"system-search-{turn.get('turn_id', 'unknown')}",
                                        'role': 'system',
                                        'content': f"Searching the web for: {search_query}...",
                                        'isSearchMessage': True,
                                        'searchQuery': search_query,  # Store the original query for easier updating
                                        'timestamp': turn.get('timestamp'),
                                        'sequenceOrder': i + 0.5  # Place between the user message and final response
                                    }
                                    frontend_messages.append(system_message)
                                    logger.info(f"DEBUG: Added system search message for query: {search_query}")
                                    continue  # Skip adding the regular assistant message with [SEARCH: ...]
                        
                        # Add the user message if not a duplicate or if it's the first occurrence
                        if 'user_input' in turn:
                            user_input = turn.get('user_input', '')
                            
                            # Only add if it's the first occurrence of this input
                            if user_input in user_prompt_order and user_prompt_order[user_input] == i and user_input not in processed_user_inputs:
                                user_message = {
                                    'id': f"user-{turn.get('turn_id', 'unknown')}",
                                    'role': 'user',
                                    'content': user_input,
                                    'timestamp': turn.get('timestamp'),
                                    'sequenceOrder': i  # Preserve original sequence
                                }
                                frontend_messages.append(user_message)
                                processed_user_inputs.add(user_input)  # Mark as processed
                                logger.info(f"DEBUG: Added user message: {user_input[:30]}... (first occurrence)")
                        
                        # Add the assistant message if present and not a search signal
                        if 'llm_output' in turn and 'llm_response' in turn['llm_output'] and 'response_tiers' in turn['llm_output']['llm_response']:
                            # Use tier3 for the highest quality response
                            content = turn['llm_output']['llm_response']['response_tiers'].get('tier3', '')
                            # If tier3 is empty, try tier2, then tier1
                            if not content:
                                content = turn['llm_output']['llm_response']['response_tiers'].get('tier2', '')
                            if not content:
                                content = turn['llm_output']['llm_response']['response_tiers'].get('tier1', '')
                            
                            # Skip search signals as they're handled above
                            if not (content and '[SEARCH:' in content):
                                assistant_message = {
                                    'id': f"assistant-{turn.get('turn_id', 'unknown')}",
                                    'role': 'assistant',
                                    'content': content,
                                    'timestamp': turn.get('timestamp'),
                                    'sequenceOrder': i + 1  # Place after corresponding user message and system message
                                }
                                frontend_messages.append(assistant_message)
                                logger.info(f"DEBUG: Added assistant message: {content[:30]}...")
                    
                    # Sort by sequence order to maintain chronological flow
                    frontend_messages.sort(key=lambda msg: msg.get('sequenceOrder', 0))
                    
                    # Remove the temporary sequenceOrder field
                    for msg in frontend_messages:
                        if 'sequenceOrder' in msg:
                            del msg['sequenceOrder']
                    
                    logger.info(f"DEBUG: Manually created {len(frontend_messages)} frontend messages")
                    
                    logger.info(f"DEBUG: First frontend message format: {frontend_messages[0] if frontend_messages else 'No messages'}")
                    logger.info(f"DEBUG: Returning success response with {len(frontend_messages)} messages")
                    return jsonify({
                        "session_id": session_id,
                        "messages": frontend_messages,
                        "status": "success",
                        "note": "This is a manual debug response"
                    })
        except Exception as e:
            logger.error(f"Error in manual debug section: {e}", exc_info=True)
    
    try:
        # Get the user-specific ChatFileManager
        managers = user_session_manager.get_user_managers(user_id)
        chat_file_manager = managers['cfm']
        
        # DEBUG logging
        logger.info(f"DEBUG: About to get transcript for user {user_id}, session {session_id}")
        transcript_file_path = chat_file_manager._get_session_transcript_path(user_id=user_id, session_id=session_id)
        logger.info(f"DEBUG: Transcript file path: {transcript_file_path}")
        logger.info(f"DEBUG: Transcript file exists: {os.path.exists(transcript_file_path)}")
        
        if os.path.exists(transcript_file_path):
            # Directly read and log the file contents
            try:
                with open(transcript_file_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                logger.info(f"DEBUG: Raw transcript content: {raw_content[:300]}...")
            except Exception as e:
                logger.error(f"DEBUG: Error reading transcript file directly: {e}")
        
        # Get transcript using the refactored method
        transcript_turns = chat_file_manager.get_session_transcript(user_id=user_id, session_id=session_id)
        logger.info(f"DEBUG: Transcript data retrieved: {transcript_turns is not None}")
        if transcript_turns is not None:
            logger.info(f"DEBUG: Transcript turns count: {len(transcript_turns)}")
            logger.info(f"DEBUG: First turn format: {list(transcript_turns[0].keys()) if transcript_turns else 'No turns'}")
        
        if transcript_turns is not None:
            # Convert transcript turns into the frontend message format
            frontend_messages = []
            processed_user_inputs = set()  # Track user inputs to avoid duplicates
            
            # First pass: Force include the first user message regardless of duplicates
            if transcript_turns and 'user_input' in transcript_turns[0]:
                first_user_message = {
                    'id': f"user-{transcript_turns[0].get('turn_id', 'unknown')}",
                    'role': 'user',
                    'content': transcript_turns[0].get('user_input', ''),
                    'timestamp': transcript_turns[0].get('timestamp'),
                    'sequenceOrder': 0  # Ensure it comes first
                }
                frontend_messages.append(first_user_message)
                processed_user_inputs.add(transcript_turns[0].get('user_input', ''))
                logger.info(f"DEBUG: Added first user message: {transcript_turns[0].get('user_input', '')[:30]}...")
            
            # First pass: collect all turns in chronological order to preserve the sequence
            # and identify which user prompts come first
            user_prompt_order = {}  # To track the first occurrence of each user prompt
            
            for i, turn in enumerate(transcript_turns):
                if 'user_input' in turn:
                    user_input = turn.get('user_input', '')
                    # Only track the first occurrence of each unique user input
                    if user_input not in user_prompt_order:
                        user_prompt_order[user_input] = i
            
            # Second pass: process turns in order but respect the first occurrence of user messages
            for i, turn in enumerate(transcript_turns):
                # Process search signals in LLM response
                if 'llm_output' in turn and 'llm_response' in turn['llm_output'] and 'response_tiers' in turn['llm_output']['llm_response']:
                    tier3_content = turn['llm_output']['llm_response']['response_tiers'].get('tier3', '')
                    
                    # Check for search signals like [SEARCH: query]
                    if tier3_content and '[SEARCH:' in tier3_content:
                        # Extract the search query
                        search_match = re.search(r'\[SEARCH:\s*([^\]]+)\]', tier3_content)
                        if search_match:
                            search_query = search_match.group(1).strip()
                            # Add a system message for the search instead of showing the raw [SEARCH: ...] text
                            system_message = {
                                'id': f"system-search-{turn.get('turn_id', 'unknown')}",
                                'role': 'system',
                                'content': f"Searching the web for: {search_query}...",
                                'isSearchMessage': True,
                                'searchQuery': search_query,  # Store the original query for easier updating
                                'timestamp': turn.get('timestamp'),
                                'sequenceOrder': i + 0.5  # Place between the user message and final response
                            }
                            frontend_messages.append(system_message)
                            logger.info(f"DEBUG: Added system search message for query: {search_query}")
                            continue  # Skip adding the regular assistant message with [SEARCH: ...]
                
                # Add the user message if not a duplicate or if it's the first occurrence
                if 'user_input' in turn:
                    user_input = turn.get('user_input', '')
                    
                    # Only add if it's the first occurrence of this input
                    if user_input in user_prompt_order and user_prompt_order[user_input] == i and user_input not in processed_user_inputs:
                        user_message = {
                            'id': f"user-{turn.get('turn_id', 'unknown')}",
                            'role': 'user',
                            'content': user_input,
                            'timestamp': turn.get('timestamp'),
                            'sequenceOrder': i  # Preserve original sequence
                        }
                        frontend_messages.append(user_message)
                        processed_user_inputs.add(user_input)  # Mark as processed
                        logger.info(f"DEBUG: Added user message: {user_input[:30]}... (first occurrence)")
                
                # Add the assistant message if present and not a search signal
                if 'llm_output' in turn and 'llm_response' in turn['llm_output'] and 'response_tiers' in turn['llm_output']['llm_response']:
                    # Use tier3 for the highest quality response
                    content = turn['llm_output']['llm_response']['response_tiers'].get('tier3', '')
                    # If tier3 is empty, try tier2, then tier1
                    if not content:
                        content = turn['llm_output']['llm_response']['response_tiers'].get('tier2', '')
                    if not content:
                        content = turn['llm_output']['llm_response']['response_tiers'].get('tier1', '')
                    
                    # Skip search signals as they're handled above
                    if not (content and '[SEARCH:' in content):
                        assistant_message = {
                            'id': f"assistant-{turn.get('turn_id', 'unknown')}",
                            'role': 'assistant',
                            'content': content,
                            'timestamp': turn.get('timestamp'),
                            'sequenceOrder': i + 1  # Place after corresponding user message and system message
                        }
                        frontend_messages.append(assistant_message)
                        logger.info(f"DEBUG: Added assistant message: {content[:30]}...")
            
            # Sort by sequence order to maintain chronological flow
            frontend_messages.sort(key=lambda msg: msg.get('sequenceOrder', 0))
            
            # Remove the temporary sequenceOrder field
            for msg in frontend_messages:
                if 'sequenceOrder' in msg:
                    del msg['sequenceOrder']
            
            logger.info(f"Successfully converted transcript data to {len(frontend_messages)} frontend messages for session {session_id}")
            
            response_data = {
                "session_id": session_id,
                "messages": frontend_messages,
                "status": "success"
            }
            logger.info(f"DEBUG: First frontend message format: {frontend_messages[0] if frontend_messages else 'No messages'}")
            logger.info(f"DEBUG: Returning success response with {len(frontend_messages)} messages")
            return jsonify(response_data)
        else:
            # get_session_transcript returns None if file not found or invalid
            logger.warning(f"DEBUG: No transcript data found for session {session_id}")
            return jsonify({
                "error": f"Session history (transcript) not found or invalid for ID: {session_id}",
                "status": "error"
            }), 404
    except Exception as e:
        logger.error(f"Error getting session history for user {user_id}, session {session_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to get session history", "status": "error"}), 500


# LLM info endpoint (remains mostly the same)
@app.route('/api/llm/info', methods=['GET'])
# @token_required # Optional: Add if needed
def llm_info():
    """Get LLM information."""
    try:
        llm_api = get_llm_api()
        model_info = {}
        if hasattr(llm_api, 'get_model_info'):
             model_info = llm_api.get_model_info()
        return jsonify({
            "model_info": model_info,
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error getting LLM info: {e}", exc_info=True)
        return jsonify({"error": "Failed to get LLM info", "status": "error"}), 500

# Removed old /api/llm/generate endpoint as chat handles generation


# --- Main Execution ---
if __name__ == '__main__':
    # Ensure waitress is installed or provide fallback
    try:
        from waitress import serve
        is_waitress_available = True
    except ImportError:
        is_waitress_available = False
        logger.warning("Waitress not found. Falling back to Flask development server (NOT recommended for production).")

    # Use environment variable RAI_API_PORT set by start_all.py, default to 6102 if not set
    port = int(os.environ.get('RAI_API_PORT', 6102))
    logger.info(f"Attempting to start RAI API Server on port {port}")

    try:
        # Use waitress if available (recommended for production)
        if is_waitress_available:
            logger.info("Starting server with Waitress...")
            print(f"RAI API Server is running at http://localhost:{port}")
            # Listen on all interfaces (both IPv4 and IPv6)
            serve(app, host='0.0.0.0', port=port, threads=8)
        else:
            logger.info("Starting server with Flask development server...")
            app.run(host='0.0.0.0', port=port, debug=False) # debug=False for production fallback
    except OSError as e:
         if "address already in use" in str(e).lower():
              logger.critical(f"FATAL: Port {port} is already in use. Please ensure no other process is running on this port.")
         else:
              logger.critical(f"FATAL: Failed to start server due to OS error: {e}", exc_info=True)
         sys.exit(f"Server Start Error: {e}")
    except Exception as e:
         logger.critical(f"FATAL: Failed to start server: {e}", exc_info=True)
         sys.exit(f"Server Start Error: {e}")
