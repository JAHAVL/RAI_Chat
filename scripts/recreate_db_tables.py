#!/usr/bin/env python3
"""
Script to recreate all database tables, including the system_messages table.
This script will ensure all tables defined in models.py exist in the database.
"""

import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("db_recreate")

# Add the parent directory to the path so we can import the necessary modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

try:
    # Import database modules
    from backend.core.database.models import Base
    from sqlalchemy import create_engine
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    env_path = parent_dir / 'backend' / '.env'
    load_dotenv(env_path)
    
    # Get MySQL connection parameters from environment variables
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', '')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'rai_chat')
    
    # Construct MySQL connection string
    connection_string = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    
    logger.info(f"Connecting to database at: {mysql_host}:{mysql_port}/{mysql_database}")
    logger.info(f"Using user: {mysql_user}")
    
    # Create SQLAlchemy engine
    engine = create_engine(connection_string)
    
    # Create all tables defined in models.py
    logger.info("Creating all tables...")
    Base.metadata.create_all(engine)
    
    logger.info("All tables created successfully!")
    
    # Check that the system_messages table exists
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if 'system_messages' in tables:
        logger.info("✅ system_messages table exists!")
    else:
        logger.error("❌ system_messages table was not created!")
    
    # Log all created tables
    logger.info(f"All tables in database: {', '.join(tables)}")
    
except Exception as e:
    logger.error(f"Error recreating database tables: {e}")
    sys.exit(1)
    
logger.info("Database tables recreation complete.")
sys.exit(0)
