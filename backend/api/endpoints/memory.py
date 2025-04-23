# RAI_Chat/backend/api/memory.py
"""
-------------------------------------------------------------------------
FILE PURPOSE (FOR NON-DEVELOPERS):

This file ONLY defines the API endpoints (access points) for AI memory.
It does NOT implement the actual memory functionality - it just receives
requests about AI memories and routes them to the appropriate services.

Endpoints defined here:
- /memory - Gets facts the AI has remembered about a user

Think of this file as the library desk where you request information,
but the librarian (memory service) is the one who actually retrieves
the books. This file is just the access point for memory requests.
-------------------------------------------------------------------------
"""
import logging
from flask import Blueprint, request, jsonify, g
from core.auth.utils import token_required
from managers.session import get_user_session_manager

memory_bp = Blueprint('memory', __name__)
logger = logging.getLogger(__name__)

@memory_bp.route('/', methods=['GET'])
@token_required
def get_memory():
    """Get memory contents (user remembered facts) for the authenticated user"""
    try:
        # Get user ID from auth token
        user_id = g.user_id
        
        # Get database session
        from ..core.database.session import get_db
        db = get_db()
        
        # Get user session manager
        user_session_manager = get_user_session_manager(user_id)
        
        # Get remembered facts from the user record
        user_record = user_session_manager.get_user_record(db)
        
        if not user_record:
            return jsonify({
                'error': 'User record not found',
                'status': 'error'
            }), 404
        
        # Return the remembered facts
        return jsonify({
            'memory': user_record.remembered_facts or [],
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Error getting memory for user {g.user_id}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to get memory',
            'status': 'error'
        }), 500
