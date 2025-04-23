#!/usr/bin/env python
# RAI_Chat/backend/core/database/update_schema.py
"""
Database schema update script to add the remembered_facts column to the users table.
This is a one-time migration to update the schema without losing data.
"""

import logging
import sys
import os
from sqlalchemy import Column, JSON, text
from sqlalchemy.exc import SQLAlchemyError

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Use absolute imports
from core.database.connection import get_db, engine
from core.database.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_schema():
    """Update the database schema to include the remembered_facts column."""
    try:
        # Check if the column exists
        with engine.connect() as conn:
            # Check if column exists in MySQL
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_NAME = 'users' "
                "AND COLUMN_NAME = 'remembered_facts' "
                "AND TABLE_SCHEMA = (SELECT DATABASE())"
            ))
            column_exists = result.scalar() > 0
            
            if not column_exists:
                logger.info("Adding remembered_facts column to users table...")
                conn.execute(text(
                    "ALTER TABLE users "
                    "ADD COLUMN remembered_facts JSON NULL"
                ))
                conn.commit()
                logger.info("Column added successfully.")
            else:
                logger.info("remembered_facts column already exists.")
                
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting schema update...")
    success = update_schema()
    if success:
        logger.info("Schema update completed successfully.")
    else:
        logger.error("Schema update failed.")
