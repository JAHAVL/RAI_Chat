"""
Auto-migration module that runs when the application starts.
Automatically adds any missing columns needed for the unified memory architecture.
"""
import logging
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logger = logging.getLogger(__name__)

def run_auto_migration(engine):
    """
    Automatically run migrations for unified memory architecture.
    This runs at application startup to ensure database schema is up-to-date.
    
    Args:
        engine: SQLAlchemy engine connected to the database
    """
    try:
        # Create inspector to check existing columns
        inspector = inspect(engine)
        
        # Get existing columns
        columns = [col['name'] for col in inspector.get_columns('messages')]
        logger.info(f"Existing columns in messages table: {columns}")
        
        with engine.begin() as connection:
            # Add memory_status column if it doesn't exist
            if 'memory_status' not in columns:
                logger.info("Adding memory_status column to messages table")
                connection.execute(text("ALTER TABLE messages ADD COLUMN memory_status VARCHAR(20) DEFAULT 'contextual'"))
            
            # Add last_accessed column if it doesn't exist
            if 'last_accessed' not in columns:
                logger.info("Adding last_accessed column to messages table")
                connection.execute(text("ALTER TABLE messages ADD COLUMN last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            
            # Add importance_score column if it doesn't exist
            if 'importance_score' not in columns:
                logger.info("Adding importance_score column to messages table")
                connection.execute(text("ALTER TABLE messages ADD COLUMN importance_score INTEGER DEFAULT 1"))
        
        # Check existing indexes
        indexes = inspector.get_indexes('messages')
        index_names = [idx['name'] for idx in indexes]
        logger.info(f"Existing indexes on messages table: {index_names}")
        
        with engine.begin() as connection:
            # Create memory_status index if it doesn't exist
            if 'ix_messages_memory_status' not in index_names:
                logger.info("Creating memory_status index")
                connection.execute(text("CREATE INDEX ix_messages_memory_status ON messages (memory_status)"))
            
            # Create last_accessed index if it doesn't exist
            if 'ix_messages_last_accessed' not in index_names:
                logger.info("Creating last_accessed index")
                connection.execute(text("CREATE INDEX ix_messages_last_accessed ON messages (last_accessed)"))
        
        logger.info("Auto-migration for unified memory architecture completed successfully")
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"Error during auto-migration: {e}")
        return False
