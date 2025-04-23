#!/usr/bin/env python
"""
Launcher script for the RAI Chat backend server.
This script sets up the proper Python path and then launches the Flask app.
"""
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up the environment for the backend server"""
    # Add the backend directory to the Python path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(backend_dir)
    
    # Add both to Python path to ensure imports work
    sys.path.insert(0, backend_dir)
    sys.path.insert(0, parent_dir)
    
    # Set environment variables
    os.environ['PYTHONPATH'] = f"{backend_dir}:{parent_dir}"
    os.environ['FLASK_APP'] = 'app.py'
    os.environ['FLASK_ENV'] = 'development'
    
    # List of potential .env file locations
    env_paths = [
        Path(backend_dir) / '.env',
        Path(backend_dir) / 'Backend' / '.env',
        Path(backend_dir) / 'backend' / '.env',
        Path(parent_dir) / '.env',
    ]
    
    # Try to import dotenv
    try:
        from dotenv import load_dotenv
        
        # Try to load .env from all potential locations
        for env_path in env_paths:
            if env_path.exists():
                logger.info(f"Loading environment variables from: {env_path}")
                load_dotenv(dotenv_path=env_path)
                break
    except ImportError:
        logger.warning("python-dotenv not installed, environment variables may not be loaded properly")
    
    # Check if Tavily API key is loaded
    tavily_key = os.environ.get('TAVILY_API_KEY')
    if tavily_key:
        logger.info(f"Successfully loaded TAVILY_API_KEY: {tavily_key[:4]}...{tavily_key[-4:]}")
    else:
        logger.warning("TAVILY_API_KEY not found in environment variables")

def run_server():
    """Run the Flask server"""
    # Set up the environment first
    setup_environment()
    
    try:
        # Import the Flask app here after environment is set up
        import app
        logger.info("Starting Flask server...")
        # Run the app
        app.create_app().run(
            host='0.0.0.0',
            port=6102,
            debug=True
        )
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_server()
