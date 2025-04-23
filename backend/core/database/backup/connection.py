# RAI_Chat/backend/core/database/connection.py

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Rename to avoid conflict
from contextlib import contextmanager
from typing import Generator

# Placeholder for configuration loading - replace with actual implementation later
# This function should retrieve the database connection string
# (e.g., "mysql+mysqlconnector://user:password@host/db_name")
# from environment variables or a config file.
def get_database_url() -> str:
    """Retrieves the database URL from config, always using SQLite."""
    # Import here to avoid circular imports
    import os
    from config import AppConfig, get_config
    
    # Get DATABASE_URL from get_config function which now always returns SQLite
    config = get_config()
    DATABASE_URL = config.get('DATABASE_URL')
    
    # Double-check that we're using SQLite
    if DATABASE_URL and 'sqlite' in DATABASE_URL:
        logging.info(f"Using SQLite database URL from config: {DATABASE_URL}")
        return DATABASE_URL
    
    # Force SQLite if somehow the config didn't provide a SQLite URL
    logging.warning("Config did not provide a SQLite URL, forcing SQLite database.")
    os.makedirs(AppConfig.DATA_DIR, exist_ok=True)
    db_path = os.path.join(AppConfig.DATA_DIR, 'rai_chat.db')
    sqlite_url = f"sqlite:///{db_path}"
    logging.info(f"Using SQLite database at: {db_path}")
    return sqlite_url

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
    
    # Import the Base and models to create tables
    from .models import Base, User, Session
    
    # Create all tables if they don't exist
    logging.info("Creating database tables if they don't exist...")
    Base.metadata.create_all(engine)
    logging.info("Database tables created or already exist.")
    
    # Create a default user if none exists
    SessionTemp = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionTemp()
    try:
        default_user = db_session.query(User).filter(User.user_id == 1).first()
        if not default_user:
            logging.info("Creating default user...")
            default_user = User(
                user_id=1,
                username="default_user",
                email="default@example.com",
                auth_provider="local"
            )
            db_session.add(default_user)
            db_session.commit()
            logging.info("Default user created.")
        else:
            logging.info("Default user already exists.")
    except Exception as e:
        db_session.rollback()
        logging.error(f"Error creating default user: {e}")
    finally:
        db_session.close()
    
except ImportError as e:
    logging.error(f"Database driver error: {e}. Ensure mysql-connector-python is installed.")
    raise
except Exception as e:
    logging.error(f"Error creating database engine or initializing tables: {e}")
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
# from .connection import get_db
#
# with get_db() as db:
#     # Perform database operations using db session
#     user = db.query(User).filter(User.username == "test").first()