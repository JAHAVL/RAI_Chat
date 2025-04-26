"""
Common utilities for API handlers.

This file contains shared functionality for all API handlers.
"""

import logging
from typing import Dict, Any, Generator
from flask import jsonify, Response

# Create logger
logger = logging.getLogger(__name__)

def create_error_response(message: str, status_code: int = 400) -> tuple:
    """Create a standardized error response"""
    return jsonify({
        'status': 'error',
        'message': message
    }), status_code

def create_success_response(data: Dict[str, Any] = None) -> tuple:
    """Create a standardized success response"""
    response = {'status': 'success'}
    if data:
        response.update(data)
    return jsonify(response), 200

def stream_response(generator: Generator) -> Response:
    """Create a streaming response from a generator"""
    return Response(generator, mimetype='application/x-ndjson')
