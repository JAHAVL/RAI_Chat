"""
Health check handlers for API routes.

This module contains handlers for health check and system status endpoints.
"""

import logging
import time
from importlib.metadata import version
from .common import create_error_response, create_success_response

# Create logger
logger = logging.getLogger(__name__)

def handle_health_check():
    """Handler for API health check endpoint"""
    try:
        try:
            # Get app version
            app_version = version('rai_chat_backend')
        except:
            app_version = 'unknown'
        
        # Basic health check
        return create_success_response({
            'status': 'healthy',
            'version': app_version,
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500
