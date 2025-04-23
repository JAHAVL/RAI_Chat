# RAI_Chat/backend/app.py
import os
import logging
import json
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from datetime import datetime
import time
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_app(config_object=None):
    """Application factory pattern for Flask app"""
    app = Flask(__name__)
    
    # Configure the app
    if config_object:
        app.config.from_object(config_object)
    else:
        # Default configuration
        from config import get_config
        app.config.from_object(get_config())
        
    # Configure Flask to not truncate JSON responses
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    app.json.sort_keys = False
    app.json.compact = True
    
    # Initialize extensions with proper CORS settings
    CORS(app, 
         resources={r"/api/*": {
             "origins": ["http://localhost:8081"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"]
         }},
         supports_credentials=True)
    
    # Add OPTIONS method handler for all routes to handle preflight requests
    @app.route('/api/<path:path>', methods=['OPTIONS'])
    def options_handler(path):
        return '', 200
    
    # Initialize logging
    configure_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    return app

def configure_logging(app):
    """Configure logging for the application"""
    from utils.path import BACKEND_LOGS_DIR
    
    # We don't need to create the directory as it's handled in path.py
    # Use iso date format in filename for better sorting
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d')
    log_file = os.path.join(BACKEND_LOGS_DIR, f'backend_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ],
        force=True
    )
    
    return logging.getLogger(__name__)

def register_blueprints(app):
    """Register Flask blueprints"""
    try:
        # Set up proper import paths
        import sys
        import os
        # Add the current directory to sys.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Import all blueprints with proper path handling
        sys.path.insert(0, os.path.join(current_dir, 'api'))
        
        # Import blueprints from the new endpoints directory
        import api.endpoints.auth
        app.register_blueprint(api.endpoints.auth.auth_bp, url_prefix='/api/auth')
        app.logger.info("Auth blueprint registered successfully")
        
        import api.endpoints.chat
        app.register_blueprint(api.endpoints.chat.chat_bp, url_prefix='/api/chat')
        app.logger.info("Chat blueprint registered successfully")
        
        import api.endpoints.session
        app.register_blueprint(api.endpoints.session.session_bp, url_prefix='/api/sessions')
        app.logger.info("Session blueprint registered successfully")
        
        import api.endpoints.memory
        app.register_blueprint(api.endpoints.memory.memory_bp, url_prefix='/api/memory')
        app.logger.info("Memory blueprint registered successfully")
        
        # Register the system_messages blueprint
        import api.endpoints.system_messages
        app.register_blueprint(api.endpoints.system_messages.system_messages_bp, url_prefix='/api/system-messages')
        app.logger.info("System Messages blueprint registered successfully")
        
        # Import our test search blueprint
        from api.endpoints.test_search import test_search_bp
        
        # Register the test search blueprint
        app.register_blueprint(test_search_bp)
        app.logger.info("Test Search blueprint registered successfully")
        
        # Add a basic health check endpoint
        @app.route('/api/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'success',
                'message': 'API server is running'
            })
        
        # Define a simple test endpoint for debugging
        @app.route('/api/test', methods=['GET'])
        def test_endpoint():
            """Simple test endpoint for debugging"""
            return jsonify({
                'status': 'success',
                'message': 'Test endpoint is working'
            })
        
        # Define a simple test endpoint to verify connectivity
        @app.route('/api/test-connectivity', methods=['GET'])
        def test_connectivity_endpoint():
            """Simple test endpoint to verify connectivity."""
            return jsonify({
                'message': 'Backend connection successful',
                'status': 'ok',
                'timestamp': datetime.now().isoformat()
            })
        
        # Add a sessions endpoint to return mock session data
        @app.route('/api/sessions', methods=['GET'])
        def sessions_endpoint():
            """Return mock session data for development."""
            # In a real implementation, this would query the database
            mock_sessions = [
                {
                    "id": "session1",
                    "title": "Development Session 1",
                    "timestamp": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat()
                },
                {
                    "id": "session2",
                    "title": "Development Session 2",
                    "timestamp": datetime.now().isoformat(),
                    "last_modified": datetime.now().isoformat()
                }
            ]
            return jsonify(mock_sessions)
        
        # Define a home route
        @app.route('/', methods=['GET'])
        def home():
            """Home route."""
            return jsonify({
                'message': 'RAI Chat API is running',
                'status': 'ok'
            })
        
        app.logger.info("Basic endpoints registered successfully")
            
    except Exception as e:
        app.logger.error(f"Error registering blueprints: {e}", exc_info=True)

# This is the entry point for the application when run directly
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=6102, debug=True)
