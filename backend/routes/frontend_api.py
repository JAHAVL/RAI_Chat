"""
Frontend API routes for RAI Chat Backend.

This module serves as the single entry point for all frontend API interactions,
but delegates actual implementation to handler modules.
"""

import logging
from flask import Blueprint, jsonify, request, g
from middleware.auth import token_required

# Import handlers
from .handlers.auth import handle_login, handle_register, handle_logout, handle_get_current_user
from .handlers.chat import handle_chat, handle_chat_stream, handle_search
from .handlers.session import (
    handle_get_sessions, handle_get_session, handle_create_session, 
    handle_delete_session, handle_get_chat_history, handle_reset_session
)
from .handlers.system_message import handle_send_system_message, handle_get_system_messages, handle_get_system_message
from .handlers.health import handle_health_check

# Create logger
logger = logging.getLogger(__name__)

# Create blueprint for API routes
frontend_api = Blueprint('frontend_api', __name__, url_prefix='/api')

# --------------------------------
# Chat Endpoints
# --------------------------------

@frontend_api.route('/chat', methods=['POST'])
@token_required
def chat():
    return handle_chat()

@frontend_api.route('/chat/stream', methods=['POST'])
@token_required
def chat_stream():
    return handle_chat_stream()

# --------------------------------
# Session Endpoints
# --------------------------------

@frontend_api.route('/sessions', methods=['GET'])
@token_required
def get_sessions():
    return handle_get_sessions()

@frontend_api.route('/sessions/<session_id>', methods=['GET'])
@token_required
def get_session(session_id):
    return handle_get_session(session_id)

@frontend_api.route('/sessions', methods=['POST'])
@token_required
def create_session():
    return handle_create_session()

@frontend_api.route('/sessions/<session_id>', methods=['DELETE'])
@token_required
def delete_session(session_id):
    return handle_delete_session(session_id)

@frontend_api.route('/sessions/<session_id>/history', methods=['GET'])
@token_required
def get_chat_history(session_id):
    return handle_get_chat_history(session_id)

@frontend_api.route('/sessions/reset', methods=['POST'])
@token_required
def reset_session():
    return handle_reset_session()

# --------------------------------
# Authentication Endpoints
# --------------------------------

@frontend_api.route('/auth/login', methods=['POST'])
def login():
    return handle_login()

@frontend_api.route('/auth/register', methods=['POST'])
def register():
    return handle_register()

@frontend_api.route('/auth/logout', methods=['POST'])
@token_required
def logout():
    return handle_logout()

@frontend_api.route('/auth/me', methods=['GET'])
@token_required
def get_current_user():
    return handle_get_current_user()

# --------------------------------
# System Message Endpoints
# --------------------------------

@frontend_api.route('/system/message', methods=['POST'])
@token_required
def send_system_message():
    session_id = request.args.get('session_id')
    return handle_send_system_message(session_id)

@frontend_api.route('/system/messages/<session_id>', methods=['GET'])
@token_required
def get_system_messages(session_id):
    return handle_get_system_messages(session_id)

@frontend_api.route('/system/message', methods=['GET'])
def get_system_message():
    return handle_get_system_message()

# --------------------------------
# Health Check Endpoint
# --------------------------------

@frontend_api.route('/health', methods=['GET'])
def health_check():
    return handle_health_check()
