"""
Database connection utilities for the RAI Chat application.
"""

import os
import logging
import time
import socket
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from contextlib import contextmanager
from typing import Generator, Optional

# Import the Base class
from . import Base

# Configure logging
logger = logging.getLogger(__name__)

def get_database_url() -> str:
    """Retrieves the database URL, prioritizing MySQL for Docker environment."""
    # Get MySQL connection parameters from environment variables or use defaults
    mysql_host = os.environ.get('MYSQL_HOST', 'mysql')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', '')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'rai_chat')
    
    # Create MySQL connection URL
    database_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    logger.info(f"Using MySQL database at: {mysql_host}:{mysql_port}/{mysql_database}")
    return database_url

# Retrieve the database URL
DATABASE_URL = get_database_url()

def create_db_engine(url: str, max_retries: int = 5, retry_interval: int = 5) -> Optional[object]:
    """Create a database engine with retry logic."""
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting to connect to database (attempt {retry_count + 1}/{max_retries})")
            
            # Create the engine with connection pooling and timeout settings
            engine = create_engine(
                url,
                echo=False,
                pool_recycle=1800,  # Reconnect after 30 minutes
                pool_pre_ping=True,  # Verify connections before using
                pool_timeout=30,     # Connection timeout of 30 seconds
                connect_args={'connect_timeout': 10}  # MySQL connection timeout
            )
            
            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Database connection successful!")
                return engine
                
        except (exc.SQLAlchemyError, exc.DBAPIError) as e:
            last_error = e
            logger.warning(f"Database connection failed: {str(e)}. Retrying in {retry_interval} seconds...")
            retry_count += 1
            time.sleep(retry_interval)
    
    logger.error(f"Failed to connect to database after {max_retries} attempts. Last error: {str(last_error)}")
    return None

# Create the SQLAlchemy engine with retry logic
engine = create_db_engine(DATABASE_URL)

# If engine creation failed, use SQLite as fallback
if engine is None:
    logger.warning("Falling back to SQLite database for temporary operation")
    SQLITE_URL = "sqlite:///./rai_chat_fallback.db"
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db() -> Generator[SQLAlchemySession, None, None]:
    """
    Provide a transactional scope around a series of operations.
    
    Yields:
        SQLAlchemy Session: The database session
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

def ensure_tables_exist():
    """
    Safely ensure all tables defined in the models exist in the database.
    This will never drop tables or delete data, only create missing tables.
    """
    logger.info("Ensuring database tables exist...")
    try:
        # Create any tables that don't exist yet
        # This is safe for existing tables and won't drop data
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables check completed")
        return True
    except Exception as e:
        logger.error(f"Error ensuring database tables exist: {str(e)}")
        return False

def create_tables():
    """Create all tables defined in the models."""
    logger.info("Creating database tables if they don't exist...")
    try:
        # Check if we're in development mode
        dev_mode = os.environ.get('FLASK_ENV', 'production').lower() == 'development'
        
        if dev_mode:
            # Only drop tables in development mode
            logger.info("Development mode detected. Dropping existing tables to ensure schema consistency...")
            Base.metadata.drop_all(bind=engine)
            logger.info("Tables dropped successfully.")
        
        # Create all tables based on model definitions
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        return False

def test_db_connection() -> bool:
    """
    Test the database connection.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        # Try to connect to the database
        session = SessionLocal()
        try:
            # Execute a simple query
            session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        return False
