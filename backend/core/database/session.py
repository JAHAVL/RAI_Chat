# RAI_Chat/backend/core/database/session.py

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Rename to avoid conflict
from contextlib import contextmanager
from typing import Generator

def get_database_url() -> str:
    """Retrieves the database URL using MySQL in all environments."""
    # Get MySQL connection parameters from environment variables with defaults
    mysql_host = os.environ.get('MYSQL_HOST', 'mysql')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_user = os.environ.get('MYSQL_USER', 'rai_user')
    mysql_password = os.environ.get('MYSQL_PASSWORD', 'rai_password')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'rai_chat')
    
    # Log connection info (without password)
    logging.info(f"MySQL connection: {mysql_user}@{mysql_host}:{mysql_port}/{mysql_database}")
    
    # Return MySQL connection URL
    return f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"

# Retrieve the database URL
DATABASE_URL = get_database_url()

# Create the SQLAlchemy engine
# echo=True is useful for debugging, shows generated SQL statements
# pool_pre_ping=True helps manage connections that might have timed out
try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        # echo=True # Uncomment for debugging SQL
    )
except ImportError as e:
    logging.error(f"Database driver error: {e}. Ensure mysql-connector-python is installed.")
    raise
except Exception as e:
    logging.error(f"Error creating database engine: {e}")
    raise


# Create a configured "Session" class
# autocommit=False and autoflush=False are generally recommended defaults
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency function / Context Manager for database sessions
@contextmanager
def get_db() -> Generator[SQLAlchemySession, None, None]:
    """Provides a transactional database session context."""
    db = SessionLocal()
    try:
        yield db
        db.commit() # Commit transaction if no exceptions occurred
    except Exception:
        db.rollback() # Rollback transaction on error
        raise
    finally:
        db.close() # Always close the session

# Optional: Function to test the database connection
def test_db_connection():
    """Tests the database connection."""
    try:
        # The connection is lazy, so we need to perform an operation
        with engine.connect() as connection:
            logging.info("Database connection successful.")
            return True
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return False

# Example usage (e.g., in an API endpoint):
# from backend.core.database.session import get_db
#
# with get_db() as db:
#     # Perform database operations using db session
#     user = db.query(User).filter(User.username == "test").first()