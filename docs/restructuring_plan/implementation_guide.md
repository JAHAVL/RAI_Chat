# RAI Chat Backend Restructuring Implementation Guide

This guide provides a detailed, step-by-step approach to implementing the backend restructuring plan. The goal is to reorganize the codebase according to modern Python best practices without changing any functionality.

## Prerequisites

Before starting the restructuring process, ensure that:

1. You have a backup of the entire codebase
2. All tests are passing in the current structure
3. You have a way to verify functionality after each step (e.g., running the application)

## Phase 1: Create the New Directory Structure

```bash
# Create main package directories
mkdir -p RAI_Chat/backend/{api,core/{auth,database,logging},services/memory,utils,extensions,modules/web_search,schemas,migrations}
mkdir -p RAI_Chat/scripts
mkdir -p RAI_Chat/tests/{unit,integration}

# Create package initialization files
touch RAI_Chat/backend/__init__.py
touch RAI_Chat/backend/api/__init__.py
touch RAI_Chat/backend/core/__init__.py
touch RAI_Chat/backend/core/auth/__init__.py
touch RAI_Chat/backend/core/database/__init__.py
touch RAI_Chat/backend/core/logging/__init__.py
touch RAI_Chat/backend/services/__init__.py
touch RAI_Chat/backend/services/memory/__init__.py
touch RAI_Chat/backend/utils/__init__.py
touch RAI_Chat/backend/extensions/__init__.py
touch RAI_Chat/backend/modules/__init__.py
touch RAI_Chat/backend/modules/web_search/__init__.py
touch RAI_Chat/backend/schemas/__init__.py
touch RAI_Chat/tests/__init__.py
touch RAI_Chat/tests/unit/__init__.py
touch RAI_Chat/tests/integration/__init__.py
```

## Phase 2: Create Core Application Files

### Step 1: Create the Application Factory

Create `RAI_Chat/backend/app.py`:

```python
# RAI_Chat/backend/app.py
import os
import logging
from flask import Flask
from flask_cors import CORS

def create_app(config_object=None):
    """Application factory pattern for Flask app"""
    app = Flask(__name__)
    
    # Configure the app
    if config_object:
        app.config.from_object(config_object)
    else:
        # Default configuration
        from .config import get_config
        app.config.from_object(get_config())
    
    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize logging
    configure_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    return app

def configure_logging(app):
    """Configure logging for the application"""
    from .utils.path import LOGS_DIR
    import os
    
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, 'rai_api_server.log')
    
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
    # Import blueprints
    from .api.auth import auth_bp
    from .api.chat import chat_bp
    from .api.memory import memory_bp
    from .api.session import session_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(memory_bp, url_prefix='/api/memory')
    app.register_blueprint(session_bp, url_prefix='/api/session')
```

### Step 2: Create the WSGI Entry Point

Create `RAI_Chat/backend/wsgi.py`:

```python
# RAI_Chat/backend/wsgi.py
from .app import create_app

app = create_app()

if __name__ == '__main__':
    import os
    
    # Use environment variable RAI_API_PORT, default to 6102 if not set
    port = int(os.environ.get('RAI_API_PORT', 6102))
    
    # Try to use waitress if available, otherwise fall back to Flask dev server
    try:
        from waitress import serve
        print(f"RAI API Server is running at http://localhost:{port}")
        serve(app, host='0.0.0.0', port=port, threads=8)
    except ImportError:
        print(f"Waitress not found. Using Flask development server (not recommended for production).")
        app.run(host='0.0.0.0', port=port, debug=False)
```

### Step 3: Create the Configuration Module

Create `RAI_Chat/backend/config.py`:

```python
# RAI_Chat/backend/config.py
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-key-please-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{BASE_DIR}/instance/rai_chat.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # LLM API
    LLM_API_URL = os.environ.get('LLM_API_URL', 'http://localhost:6301')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # In production, ensure these are set in environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

def get_config():
    """Return the appropriate configuration object based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig
```

## Phase 3: Implement API Blueprints

### Step 1: Create API Blueprint Registration

Create `RAI_Chat/backend/api/__init__.py`:

```python
# RAI_Chat/backend/api/__init__.py
# This file will be populated with blueprint imports later
```

### Step 2: Create Auth Blueprint

Create `RAI_Chat/backend/api/auth.py`:

```python
# RAI_Chat/backend/api/auth.py
import logging
from flask import Blueprint, request, jsonify
from ..core.auth.service import AuthService
from ..core.database.session import get_db

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/register', methods=['POST'])
def register_user():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'error': 'Username and password are required',
                'status': 'error'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        # Use the database session
        db = get_db()
        
        # Use the auth service
        auth_service = AuthService()
        result = auth_service.register(db, username, password)
        
        if result.get('status') == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to register user',
            'status': 'error'
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login_user():
    """Log in a user"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({
                'error': 'Username and password are required',
                'status': 'error'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        # Use the database session
        db = get_db()
        
        # Use the auth service
        auth_service = AuthService()
        result = auth_service.login(db, username, password)
        
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"Error logging in user: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to log in',
            'status': 'error'
        }), 500
```

### Step 3: Create Chat Blueprint

Create `RAI_Chat/backend/api/chat.py`:

```python
# RAI_Chat/backend/api/chat.py
import logging
from flask import Blueprint, request, jsonify, g, Response
from ..core.auth.utils import token_required
from ..services.session import get_user_session_manager

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

@chat_bp.route('/', methods=['POST'])
@token_required
def chat():
    """Chat endpoint using conversation manager, supporting streaming"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'message' not in data:
            return jsonify({
                'error': 'Message is required',
                'status': 'error'
            }), 400
        
        user_input = data.get('message')
        session_id = data.get('session_id')  # Optional
        streaming = data.get('streaming', False)  # Default to non-streaming
        
        # Get user ID from auth token
        user_id = g.user_id
        
        # Get database session
        from ..core.database.session import get_db
        db = get_db()
        
        # Get user session manager
        user_session_manager = get_user_session_manager(user_id)
        
        # Get conversation manager
        conversation_manager = user_session_manager.get_conversation_manager()
        
        # Load or create session
        if session_id:
            conversation_manager.load_chat(session_id)
        else:
            conversation_manager.start_new_chat()
            session_id = conversation_manager.current_session_id
        
        # Handle streaming response if requested
        if streaming:
            def stream_response():
                for update in conversation_manager.get_response(db, user_input):
                    # Convert update to JSON string and yield
                    yield f"data: {json.dumps(update)}\n\n"
            
            # Create streaming response
            return Response(
                stream_response(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no'
                }
            )
        else:
            # Non-streaming response
            response_data = None
            for update in conversation_manager.get_response(db, user_input):
                response_data = update
            
            # Save the chat after processing
            conversation_manager.save_current_chat(db)
            
            # Return the final response
            return jsonify({
                'response': response_data.get('response', ''),
                'session_id': session_id,
                'status': 'success'
            })
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to process chat request',
            'status': 'error'
        }), 500
```

Continue implementing the remaining API blueprints (memory.py and session.py) in a similar manner.

## Phase 4: Move and Update Core Components

### Step 1: Update Auth Components

Copy the existing auth files to the new structure and update imports:

```bash
cp RAI_Chat/Backend/core/auth/models.py RAI_Chat/backend/core/auth/
cp RAI_Chat/Backend/core/auth/service.py RAI_Chat/backend/core/auth/
cp RAI_Chat/Backend/core/auth/strategies.py RAI_Chat/backend/core/auth/
cp RAI_Chat/Backend/core/auth/utils.py RAI_Chat/backend/core/auth/
```

Update imports in each file to use the new structure.

### Step 2: Update Database Components

Copy the existing database files to the new structure and update imports:

```bash
cp RAI_Chat/Backend/core/database/connection.py RAI_Chat/backend/core/database/session.py
cp RAI_Chat/Backend/core/database/models.py RAI_Chat/backend/core/database/
```

Update imports in each file to use the new structure.

## Phase 5: Move and Update Services

### Step 1: Move Manager Classes to Services

```bash
cp RAI_Chat/Backend/managers/conversation_manager.py RAI_Chat/backend/services/conversation.py
cp RAI_Chat/Backend/managers/chat_file_manager.py RAI_Chat/backend/services/file_storage.py
cp RAI_Chat/Backend/managers/user_session_manager.py RAI_Chat/backend/services/session.py
cp RAI_Chat/Backend/managers/memory/contextual_memory.py RAI_Chat/backend/services/memory/contextual.py
cp RAI_Chat/Backend/managers/memory/episodic_memory.py RAI_Chat/backend/services/memory/episodic.py
```

Update imports in each file to use the new structure.

### Step 2: Move Component Classes to Services

```bash
cp RAI_Chat/Backend/components/action_handler.py RAI_Chat/backend/services/action_handler.py
cp RAI_Chat/Backend/components/prompt_builder.py RAI_Chat/backend/services/prompt_builder.py
cp RAI_Chat/Backend/components/prompts.py RAI_Chat/backend/services/prompts.py
```

Update imports in each file to use the new structure.

## Phase 6: Move and Update Utilities

```bash
cp RAI_Chat/Backend/utils/module_loader.py RAI_Chat/backend/utils/
```

Create a consolidated path utility:

```bash
# Combine path_finder.py and path_manager.py into a single path.py
touch RAI_Chat/backend/utils/path.py
```

## Phase 7: Move and Update Modules

```bash
cp RAI_Chat/Backend/Built_in_modules/web_search_module/tavily_client.py RAI_Chat/backend/modules/web_search/tavily.py
```

Update imports in each file to use the new structure.

## Phase 8: Move and Update Scripts

```bash
cp RAI_Chat/Backend/Launch_App.py RAI_Chat/scripts/launch_app.py
cp RAI_Chat/Backend/scripts/*.py RAI_Chat/scripts/
```

Update the launch script to use the new structure:

```python
# RAI_Chat/scripts/launch_app.py
#!/usr/bin/env python3
import subprocess
import signal
import os
import sys
import time
import logging
from pathlib import Path

# --- Configuration ---
LLM_API_PORT = 6301
RAI_API_PORT = 6102

# --- Logging Setup ---
LOG_DIR = Path(__file__).parent.parent / "backend" / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "launch_app.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AppLauncher")

# --- Project Paths ---
SCRIPTS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPTS_DIR.parent.parent.resolve()
LLM_ENGINE_DIR = PROJECT_ROOT / "llm_Engine"
RAI_CHAT_DIR = PROJECT_ROOT / "RAI_Chat"
BACKEND_DIR = RAI_CHAT_DIR / "backend"
FRONTEND_DIR = RAI_CHAT_DIR / "frontend"

# --- Process Management ---
# (Rest of the launch script remains the same)
```

## Phase 9: Move and Update Tests

```bash
mkdir -p RAI_Chat/tests/unit
mkdir -p RAI_Chat/tests/integration

# Move tests to appropriate directories
cp RAI_Chat/Backend/tests/test_*.py RAI_Chat/tests/unit/
```

Create a test configuration file:

```bash
touch RAI_Chat/tests/conftest.py
```

## Phase 10: Testing and Verification

1. Run the application using the new structure:
   ```bash
   python RAI_Chat/scripts/launch_app.py
   ```

2. Test all functionality to ensure it works as expected.

3. Run all tests to ensure they pass with the new structure.

## Phase 11: Clean Up

Once everything is working correctly, you can remove the old structure:

```bash
# Backup the old structure first
cp -r RAI_Chat/Backend RAI_Chat/Backend_old

# Remove the old structure
rm -rf RAI_Chat/Backend
```

## Conclusion

This implementation guide provides a step-by-step approach to restructuring the RAI Chat backend according to modern Python best practices. By following this guide, you can reorganize the codebase without changing any functionality, making it more maintainable, scalable, and testable.
