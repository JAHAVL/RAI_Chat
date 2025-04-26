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
         resources={r"/api*": {
             "origins": ["http://localhost:8081"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"]
         }},
         supports_credentials=True)
    
    # Add OPTIONS method handler for all routes to handle preflight requests
    @app.route('/api', methods=['OPTIONS'])
    @app.route('/api/<path:path>', methods=['OPTIONS'])
    def options_handler(path=''):
        return '', 200
    
    # Initialize logging
    configure_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    return app

def configure_logging(app):
    """Configure logging for the application"""
    from utils.pathconfig import BACKEND_LOGS_DIR
    
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
        # Import and register the unified frontend API blueprint from the new location
        from routes.frontend_api import frontend_api
        app.register_blueprint(frontend_api)
        
        app.logger.info("Registered unified frontend API blueprint")
        
        # Register any non-API blueprints if needed
        if app.config.get('DEBUG', False):
            from tests.test_search import test_search_bp
            app.register_blueprint(test_search_bp)
            app.logger.info("Registered test search blueprint")
            
    except Exception as e:
        app.logger.error(f"Error registering blueprints: {str(e)}", exc_info=True)

# This is the entry point for the application when run directly
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=6102, debug=True)
