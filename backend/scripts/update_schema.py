#!/usr/bin/env python
"""
Update Schema Script

This script updates the database schema to add the 'status' and 'updated_at' fields
to the SystemMessage model to support updatable system messages.
"""

import sys
import os
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import SQLAlchemy components
from sqlalchemy import text, inspect
from models.connection import get_db, ensure_tables_exist, engine

def run_schema_update():
    """Update the database schema to add status and updated_at columns to system_messages table"""
    logger.info("Running schema update for system_messages table...")
    
    try:
        # Ensure the tables exist first
        ensure_tables_exist()
        
        # Check which database dialect we're using
        dialect = engine.dialect.name
        logger.info(f"Using database dialect: {dialect}")
        
        # Now add the new columns if they don't exist
        with get_db() as db:
            inspector = inspect(engine)
            existing_columns = [col['name'] for col in inspector.get_columns('system_messages')]
            
            # Add status column if it doesn't exist
            if 'status' not in existing_columns:
                logger.info("Adding status column to system_messages table")
                db.execute(text("ALTER TABLE system_messages ADD COLUMN status VARCHAR(20) DEFAULT 'active'"))
                
                # Add index (MySQL syntax differs from SQLite)
                if dialect == 'mysql':
                    db.execute(text("CREATE INDEX idx_system_messages_status ON system_messages (status)"))
                else:
                    db.execute(text("CREATE INDEX idx_system_messages_status ON system_messages(status)"))
                    
                logger.info("Added status column to system_messages table")
            else:
                logger.info("Status column already exists in system_messages table")
            
            # Add updated_at column if it doesn't exist
            if 'updated_at' not in existing_columns:
                logger.info("Adding updated_at column to system_messages table")
                
                # Handle different SQL syntax for different databases
                if dialect == 'mysql':
                    db.execute(text("ALTER TABLE system_messages ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
                else:
                    # SQLite doesn't support ON UPDATE, we'll handle this in the code
                    db.execute(text("ALTER TABLE system_messages ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                
                logger.info("Added updated_at column to system_messages table")
            else:
                logger.info("updated_at column already exists in system_messages table")
            
        logger.info("Schema update completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating schema: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_schema_update()
    exit_code = 0 if success else 1
    sys.exit(exit_code)
