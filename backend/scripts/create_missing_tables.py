#!/usr/bin/env python
"""
Script to create missing database tables based on SQLAlchemy models.
This script will create all tables defined in the models directory that 
don't already exist in the database.

This script connects to the MySQL database running in Docker and ensures
all required tables exist, especially for video transcript retrieval.
"""

import os
import sys
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the sys.path
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent.parent

# Ensure the backend directory is in the Python path
sys.path.insert(0, str(BACKEND_DIR))

# Import SQLAlchemy and create a custom engine for MySQL
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# Import models
from models import Base
from models.user import User
from models.session import Session
from models.message import Message
from models.system_message import SystemMessage

# MySQL connection parameters for Docker container
MYSQL_HOST = "localhost"  # Use localhost since we're connecting from host machine
MYSQL_PORT = 3307         # The published port (3307 maps to container's 3306)
MYSQL_USER = "rai_user"
MYSQL_PASSWORD = "rai_password"
MYSQL_DATABASE = "rai_chat"

def get_mysql_connection_string():
    """Generate the MySQL connection string."""
    return f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

def create_missing_tables():
    """
    Create any tables defined in the models that don't exist in the database.
    """
    # Create MySQL engine
    try:
        connection_string = get_mysql_connection_string()
        logger.info(f"Connecting to MySQL database: {MYSQL_HOST}:{MYSQL_PORT}, Database: {MYSQL_DATABASE}")
        engine = create_engine(connection_string)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to MySQL database")
    except SQLAlchemyError as e:
        logger.error(f"Failed to connect to MySQL database: {e}")
        sys.exit(1)
    
    # Check which tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    logger.info(f"Existing tables: {existing_tables}")
    
    # Find our model tables that are missing
    model_tables = Base.metadata.tables.keys()
    missing_tables = [table for table in model_tables if table not in existing_tables]
    
    if not missing_tables:
        logger.info("All tables already exist! No changes needed.")
        return
    
    # Print the tables that will be created
    logger.info(f"The following tables will be created: {missing_tables}")
    
    # Create the tables
    try:
        Base.metadata.create_all(engine)
        logger.info("Tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to create tables: {e}")
        sys.exit(1)
    
    # Verify tables were created
    inspector = inspect(engine)
    updated_tables = inspector.get_table_names()
    logger.info(f"Updated tables: {updated_tables}")
    
    # Check if all tables are now present
    still_missing = [table for table in model_tables if table not in updated_tables]
    if still_missing:
        logger.error(f"WARNING: Some tables could not be created: {still_missing}")
    else:
        logger.info("Success! All missing tables have been created.")
        
    # Specifically check for tables needed for video transcript retrieval
    critical_tables = ['messages', 'system_messages']
    missing_critical = [table for table in critical_tables if table not in updated_tables]
    if missing_critical:
        logger.error(f"ERROR: Critical tables for video transcript retrieval are missing: {missing_critical}")
    else:
        logger.info("Video transcript retrieval functionality is now fully supported with all required tables.")

if __name__ == "__main__":
    print("Creating missing database tables in MySQL for the RAI Chat application...")
    create_missing_tables()
