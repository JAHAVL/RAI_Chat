"""
-------------------------------------------------------------------------
FILE PURPOSE:

This file defines the API endpoint for system messages related to chat operations.
It handles status updates, notifications, and other system-level communications
separate from the actual LLM responses.

Endpoints defined here:
- /system-messages - Accepts and returns system messages related to search status, etc.

This separation ensures clear distinction between system operational messages
and actual LLM-generated chat responses.
-------------------------------------------------------------------------
"""
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g, Response

# Use absolute imports consistently for Docker environment
from core.auth.utils import token_required

logger = logging.getLogger(__name__)

# Import database utilities
from core.database.session import get_db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

# Create a blueprint for system messages
system_messages_bp = Blueprint('system_messages', __name__)

# In-memory storage for system messages as a cache
# This is supplemented by database storage for persistence
_system_messages = {}

@system_messages_bp.route('/', methods=['POST'])
@token_required
def system_message():
    """
    System messages endpoint for operational status updates.
    This endpoint is separate from the main chat endpoint to clearly
    distinguish between system operational messages and actual responses.
    
    Expected request format:
    {
        "session_id": "unique-session-id",
        "message_type": "search_status",  # or other system message types
        "content": {
            "status": "searching",  # or "complete", "error"
            "query": "search query text",  # if applicable
            "details": "Additional details"  # optional
        }
    }
    
    Returns:
        A JSON response with the system message ID and timestamp
    """
    try:
        # Get the request data
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['session_id', 'message_type', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Extract data
        session_id = data.get('session_id')
        message_type = data.get('message_type')
        content = data.get('content')
        
        # Generate a unique message ID
        import uuid
        message_id = f"sys_{uuid.uuid4()}"
        
        # Create the system message
        system_message = {
            'id': message_id,
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': session_id,
            'message_type': message_type,
            'content': content
        }
        
        # Store the message in memory cache
        _system_messages[message_id] = system_message
        
        # Store in database for persistence
        try:
            with get_db() as db:
                # Convert content to JSON string
                content_json = json.dumps(content)
                
                # Insert into database
                db.execute(
                    text("""INSERT INTO system_messages 
                          (id, timestamp, session_id, message_type, content) 
                          VALUES (:id, :timestamp, :session_id, :message_type, :content)""")
                    .bindparams(
                        id=message_id,
                        timestamp=system_message['timestamp'],
                        session_id=session_id,
                        message_type=message_type,
                        content=content_json
                    )
                )
                db.commit()
                logger.info(f"Stored system message {message_id} in database")
        except SQLAlchemyError as e:
            logger.error(f"Database error storing system message: {str(e)}")
            # Continue even if database storage fails - we still have in-memory
        
        # Return the system message
        return jsonify({
            'status': 'success',
            'message': 'System message received',
            'system_message': system_message
        })
    
    except Exception as e:
        logger.error(f"Error processing system message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error processing system message: {str(e)}'
        }), 500

@system_messages_bp.route('/update/<message_id>', methods=['PUT', 'POST'])
@token_required
def update_system_message(message_id):
    """
    Update an existing system message by ID.
    This allows for dynamic updates to status messages as operations progress.
    
    Expected request format:
    {
        "session_id": "unique-session-id",  # Must match the original message
        "content": {
            "status": "complete",  # New status
            "message": "Updated message text",  # New message text
            "details": "Additional details"  # Any other updated fields
        }
    }
    
    Returns:
        A JSON response with the updated system message
    """
    try:
        # Check if message exists
        if message_id not in _system_messages:
            return jsonify({
                'status': 'error',
                'message': f'System message with ID {message_id} not found'
            }), 404
            
        # Get the request data
        data = request.get_json()
        
        # Validate required fields
        if 'content' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: content'
            }), 400
            
        # Extract data
        content = data.get('content')
        session_id = data.get('session_id')
        
        # Validate session ID matches if provided
        if session_id and session_id != _system_messages[message_id]['session_id']:
            return jsonify({
                'status': 'error',
                'message': 'Session ID does not match original message'
            }), 400
            
        # Update the message content and timestamp in memory
        _system_messages[message_id]['content'] = content
        _system_messages[message_id]['timestamp'] = datetime.utcnow().isoformat()
        
        # Update in database for persistence
        try:
            with get_db() as db:
                # Convert content to JSON string
                content_json = json.dumps(content)
                
                # Update in database
                db.execute(
                    text("""UPDATE system_messages 
                          SET content = :content, timestamp = :timestamp 
                          WHERE id = :id""")
                    .bindparams(
                        id=message_id,
                        timestamp=_system_messages[message_id]['timestamp'],
                        content=content_json
                    )
                )
                db.commit()
                logger.info(f"Updated system message {message_id} in database")
        except SQLAlchemyError as e:
            logger.error(f"Database error updating system message: {str(e)}")
            # Continue even if database update fails - we still have in-memory
        
        # Return the updated system message
        return jsonify({
            'status': 'success',
            'message': 'System message updated',
            'system_message': _system_messages[message_id]
        })
        
    except Exception as e:
        logger.error(f"Error updating system message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error updating system message: {str(e)}'
        }), 500
        
@system_messages_bp.route('/get/<message_id>', methods=['GET'])
@token_required
def get_system_message(message_id):
    """
    Retrieve a specific system message by ID.
    
    Returns:
        The requested system message
    """
    try:
        # Check if message exists in memory cache
        if message_id in _system_messages:
            return jsonify({
                'status': 'success',
                'system_message': _system_messages[message_id]
            })
            
        # If not in memory, try to get from database
        try:
            with get_db() as db:
                result = db.execute(
                    text("""SELECT id, timestamp, session_id, message_type, content 
                          FROM system_messages 
                          WHERE id = :id""")
                    .bindparams(id=message_id)
                ).fetchone()
                
                if result:
                    # Reconstruct the system message
                    system_message = {
                        'id': result.id,
                        'timestamp': result.timestamp,
                        'session_id': result.session_id,
                        'message_type': result.message_type,
                        'content': json.loads(result.content)
                    }
                    
                    # Cache it in memory
                    _system_messages[message_id] = system_message
                    
                    return jsonify({
                        'status': 'success',
                        'system_message': system_message
                    })
                else:
                    return jsonify({
                        'status': 'error',
                        'message': f'System message with ID {message_id} not found'
                    }), 404
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving system message: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'System message with ID {message_id} not found'
            }), 404
        
    except Exception as e:
        logger.error(f"Error retrieving system message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving system message: {str(e)}'
        }), 500
        
@system_messages_bp.route('/session/<session_id>', methods=['GET'])
@token_required
def get_session_system_messages(session_id):
    """
    Retrieve all system messages for a specific session.
    This ensures that system messages persist across page refreshes and when switching sessions.
    
    Returns:
        A list of system messages for the session
    """
    try:
        # Query database for all system messages for this session
        with get_db() as db:
            results = db.execute(
                text("""SELECT id, timestamp, session_id, message_type, content 
                      FROM system_messages 
                      WHERE session_id = :session_id 
                      ORDER BY timestamp ASC""")
                .bindparams(session_id=session_id)
            ).fetchall()
            
            # Convert to list of system messages
            system_messages = []
            for result in results:
                try:
                    system_message = {
                        'id': result.id,
                        'timestamp': result.timestamp,
                        'session_id': result.session_id,
                        'message_type': result.message_type,
                        'content': json.loads(result.content)
                    }
                    
                    # Update memory cache
                    _system_messages[result.id] = system_message
                    
                    system_messages.append(system_message)
                except Exception as e:
                    logger.error(f"Error processing system message record: {str(e)}")
            
            return jsonify({
                'status': 'success',
                'session_id': session_id,
                'system_messages': system_messages
            })
        
    except Exception as e:
        logger.error(f"Error retrieving system messages for session {session_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving system messages: {str(e)}'
        }), 500
        
@system_messages_bp.route('/ensure-table', methods=['POST'])
@token_required
def ensure_system_messages_table():
    """
    Administrative endpoint to ensure the system_messages table exists in the database.
    """
    try:
        with get_db() as db:
            # Create table if it doesn't exist with MySQL syntax
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS system_messages (
                    id VARCHAR(255) PRIMARY KEY,
                    timestamp VARCHAR(255) NOT NULL,
                    session_id VARCHAR(255) NOT NULL,
                    message_type VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    INDEX idx_system_messages_session_id (session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            db.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'System messages table created or verified'
            })
    except Exception as e:
        logger.error(f"Error creating system messages table: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error creating system messages table: {str(e)}'
        }), 500
