# RAI_Chat/backend/core/database/connection.py
# Docker-specific version with relative imports

import os
import logging
import time
import socket
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from contextlib import contextmanager
from typing import Generator, Optional
import os

# Import the Base class from the models module
from .models import Base

# Configure logging
logger = logging.getLogger(__name__)

def get_database_url() -> str:
    """Retrieves the database URL, prioritizing MySQL for Docker environment."""
    # Get MySQL connection parameters from environment variables or use defaults
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_password = os.environ.get('MYSQL_PASSWORD', 'root')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'rai_chat')
    
    # Create MySQL connection URL
    database_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    logger.info(f"Using MySQL database at: {mysql_host}:{mysql_port}/{mysql_database}")
    logger.info(f"Using MySQL database URL: {database_url}")
    return database_url

# Retrieve the database URL
DATABASE_URL = get_database_url()

# Function to create engine with retry logic
def create_db_engine(url: str, max_retries: int = 5, retry_interval: int = 5) -> Optional[object]:
    """Create a database engine with retry logic.
    
    Args:
        url: Database connection URL
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds to wait between retries
        
    Returns:
        SQLAlchemy engine or None if connection fails
    """
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting to connect to database (attempt {retry_count + 1}/{max_retries})")
            
            # First check if the host is reachable
            host = url.split('@')[1].split('/')[0].split(':')[0] if '@' in url else 'localhost'
            port = int(url.split('@')[1].split('/')[0].split(':')[1]) if '@' in url and ':' in url.split('@')[1].split('/')[0] else 3306
            
            # Try to connect to the host
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result != 0:
                logger.warning(f"Database host {host}:{port} is not reachable. Retrying in {retry_interval} seconds...")
                retry_count += 1
                time.sleep(retry_interval)
                continue
            
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

def create_tables():
    """Create all tables defined in the models."""
    logger.info("Creating database tables if they don't exist...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created or already exist.")
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        return False

def create_default_user():
    """Create a default user if no users exist."""
    from .models import User
    
    # Create a session
    session = SessionLocal()
    
    try:
        # Check if any users exist
        user_count = session.query(User).count()
        
        if user_count == 0:
            # Import password hashing utility
            from ..auth.utils import hash_password
            
            # Create default user
            default_user = User(
                username="admin",
                hashed_password=hash_password("admin")
            )
            
            # Add to session and commit
            session.add(default_user)
            session.commit()
            
            logger.info("Created default admin user.")
        else:
            logger.info("Default user already exists.")
    except Exception as e:
        logger.error(f"Error creating default user: {e}")
        session.rollback()
    finally:
        session.close()

# Initialize the database with retry logic
max_init_retries = 3
init_retry_count = 0

while init_retry_count < max_init_retries:
    try:
        if create_tables():
            create_default_user()
            break
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
    
    init_retry_count += 1
    if init_retry_count < max_init_retries:
        logger.warning(f"Retrying database initialization in 5 seconds... (attempt {init_retry_count}/{max_init_retries})")
        time.sleep(5)
    else:
        logger.error(f"Failed to initialize database after {max_init_retries} attempts.")

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
            # Use SQLAlchemy's text() function to properly format the SQL query
            from sqlalchemy import text
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
