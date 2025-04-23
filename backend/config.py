"""
Configuration management for the AI Assistant application.
Centralizes path configuration and environment-specific settings.
"""
import os
import sys
import logging
from pathlib import Path

class AppConfig:
    # Base directory - configurable via environment variable
    BASE_DIR = os.environ.get('APP_BASE_DIR', 
                             os.path.dirname(os.path.abspath(__file__)))
    
    # Data directories
    DATA_DIR = os.environ.get('APP_DATA_DIR', 
                             os.path.join(BASE_DIR, 'data'))
    VIDEO_DIR = os.path.join(DATA_DIR, 'videos')
    MEMORY_DIR = os.path.join(DATA_DIR, 'memory')
    TEMP_DIR = os.path.join(DATA_DIR, 'temp')
    SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
    
    # Environment settings
    DEBUG = os.environ.get('APP_DEBUG', 'False').lower() == 'true'
    ENVIRONMENT = os.environ.get('APP_ENVIRONMENT', 'development')
    
    # API settings
    API_HOST = os.environ.get('APP_API_HOST', '127.0.0.1')
    API_PORT = int(os.environ.get('APP_API_PORT', '5001'))  # Changed from 5000 to 5001 to avoid conflicts with AirPlay
    
    # LLM settings
    LLM_MODEL = os.environ.get('APP_LLM_MODEL', 'phi-2.Q4_K_M.gguf')
    
    # API Keys for cloud services
    CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY', '')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    # For web search functionality - uses environment variable from .env file
    # Create a .env file in the backend directory with TAVILY_API_KEY to enable web search
    TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '')
    
    # Ensure directories exist
    @classmethod
    def initialize(cls):
        """Create all necessary directories if they don't exist"""
        for directory in [cls.DATA_DIR, cls.VIDEO_DIR, cls.MEMORY_DIR, 
                          cls.TEMP_DIR, cls.SESSIONS_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        # Also create models directory
        models_dir = os.path.join(cls.BASE_DIR, 'models')
        os.makedirs(models_dir, exist_ok=True)
        
    # Helper to get absolute path for a file
    @classmethod
    def get_path(cls, relative_path):
        """Convert a relative path to absolute using the config base directories"""
        if relative_path.startswith('video/'):
            return os.path.join(cls.VIDEO_DIR, relative_path[6:])
        elif relative_path.startswith('memory/'):
            return os.path.join(cls.MEMORY_DIR, relative_path[7:])
        elif relative_path.startswith('temp/'):
            return os.path.join(cls.TEMP_DIR, relative_path[5:])
        elif relative_path.startswith('session/'):
            return os.path.join(cls.SESSIONS_DIR, relative_path[8:])
        else:
            return os.path.join(cls.DATA_DIR, relative_path)
    
    @classmethod
    def is_production(cls):
        """Check if running in production environment"""
        return cls.ENVIRONMENT.lower() == 'production'

# Initialize directories when module is imported
AppConfig.initialize()

def get_config():
    """Returns a dictionary of configuration settings for Flask."""
    # ALWAYS use SQLite for the database, ignoring any DATABASE_URL in environment variables
    os.makedirs(AppConfig.DATA_DIR, exist_ok=True)
    db_path = os.path.join(AppConfig.DATA_DIR, 'rai_chat.db')
    sqlite_url = f"sqlite:///{db_path}"
    
    # Log the database URL being used
    logging.info(f"Using SQLite database at: {db_path}")
    
    return {
        'DEBUG': AppConfig.DEBUG,
        'SECRET_KEY': os.environ.get('FLASK_SECRET_KEY', 'dev_key_for_development_only'),
        'DATABASE_URL': sqlite_url,  # Force SQLite usage regardless of environment variables
        'CORS_ORIGINS': ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:8081', 'http://127.0.0.1:8081']
    }
