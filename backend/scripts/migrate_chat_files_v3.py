import os
import shutil
import re
import json
from pathlib import Path
import logging
import sys # Import sys module

# Add project root to sys.path to allow package imports
try:
    # Assumes this script is in RAI_Chat/Backend/scripts
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    logger_sys = logging.getLogger('SysPath') # Use a specific logger
    logger_sys.info(f"Added project root to sys.path: {PROJECT_ROOT}")
except Exception as e:
     logging.getLogger('SysPath').error(f"Error adding project root to sys.path: {e}", exc_info=True)
     exit(1)
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
try:
    # Assumes this script is in RAI_Chat/Backend/scripts
    BACKEND_DIR = Path(__file__).parent.parent.resolve()
    DATA_DIR = BACKEND_DIR / "data"
    # Assuming default SQLite DB location relative to Backend dir
    # IMPORTANT: Adjust if using a different DB or location specified in env vars
    DEFAULT_DB_URL = f"sqlite:///{BACKEND_DIR / 'core' / 'database' / 'temp_dev.db'}"
    DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)

    logger.info(f"Using DATA_DIR: {DATA_DIR}")
    logger.info(f"Using DATABASE_URL: {DATABASE_URL}")

    if not DATA_DIR.is_dir():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    # Import DB model AFTER setting up paths
    from RAI_Chat.backend.core.database.models import User, Base # Import Base if needed for engine

except Exception as e:
    logger.error(f"Error during configuration or import: {e}", exc_info=True)
    exit(1)

# --- Database Setup ---
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Optional: Test connection
    with engine.connect() as connection:
        logger.info("Database connection successful.")
except Exception as e:
    logger.error(f"Failed to connect to database at {DATABASE_URL}: {e}", exc_info=True)
    exit(1)
# --- End Database Setup ---


def move_file_to_session_dir(source_path: Path, user_dir: Path, session_id: str, target_filename: str):
    """Moves a file into the correct session directory, creating it if necessary."""
    if not session_id:
        logger.warning(f"  Cannot process file {source_path.name}: Invalid session_id derived.")
        return False # Indicate failure

    target_session_dir = user_dir / session_id
    target_path = target_session_dir / target_filename
    moved = False
    try:
        target_session_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(target_path))
        logger.info(f"    Moved {source_path.name} -> {target_path.relative_to(DATA_DIR)}")
        moved = True
    except OSError as e:
        logger.error(f"    Error creating directory or moving file {source_path.name} for session {session_id}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"    Unexpected error processing file {source_path.name} for session {session_id}: {e}", exc_info=True)
    return moved

def migrate_user_facts_to_db(user_id: int, memory_dir: Path):
    """Reads remember_this.json and updates the user's DB record."""
    remember_file = memory_dir / "remember_this.json"
    if not remember_file.is_file():
        logger.info(f"  No remember_this.json found in {memory_dir}. Skipping DB update for user {user_id}.")
        return True # Nothing to migrate, consider it success for this step

    logger.info(f"  Found {remember_file}. Attempting to migrate facts to DB for user {user_id}.")
    facts_data = None
    try:
        with open(remember_file, 'r', encoding='utf-8') as f:
            facts_data = json.load(f)
        if not isinstance(facts_data, list):
            logger.error(f"  Invalid format in {remember_file}. Expected a list. Cannot migrate facts.")
            return False # Indicate failure
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"  Error reading or parsing {remember_file}: {e}. Cannot migrate facts.")
        return False # Indicate failure

    # Update database
    db: SQLAlchemySession = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.remembered_facts = facts_data
            db.commit()
            logger.info(f"    Successfully updated remembered_facts in DB for user {user_id} ({len(facts_data)} facts).")
            return True
        else:
            logger.error(f"    User {user_id} not found in DB. Cannot migrate facts.")
            return False
    except Exception as e:
        logger.error(f"    DB error updating facts for user {user_id}: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()


def migrate_user_data(user_dir: Path):
    """Migrates data for a single user to the new structure."""
    user_id_str = user_dir.name
    try:
        user_id = int(user_id_str) # Convert to int for DB query
    except ValueError:
        logger.warning(f"Skipping directory {user_dir}: Name is not a valid integer user ID.")
        return

    old_chats_dir = user_dir / "chats"
    old_memory_dir = user_dir / "memory"

    logger.info(f"Processing user: {user_id}")

    # 1. Migrate user facts from memory dir to DB
    facts_migrated = False
    if old_memory_dir.is_dir():
        facts_migrated = migrate_user_facts_to_db(user_id, old_memory_dir)
    else:
        logger.info(f"  No 'memory' directory found for user {user_id}.")
        facts_migrated = True # Nothing to migrate

    # Proceed with file structure migration only if facts migration was successful (or not needed)
    if not facts_migrated:
        logger.error(f"  Skipping file structure migration for user {user_id} due to fact migration failure.")
        return

    # 2. Handle 'chats' directory migration
    if not old_chats_dir.is_dir():
        logger.info(f"  No 'chats' directory found for user {user_id}. File structure migration not needed.")
    else:
        # 2a. Move existing session directories from 'chats' to user dir
        logger.info(f"  Checking for existing session directories in {old_chats_dir}...")
        items_in_chats = list(old_chats_dir.iterdir()) # Get list before iterating/moving
        for item in items_in_chats:
            if item.is_dir():
                session_id = item.name
                target_session_dir = user_dir / session_id
                if target_session_dir.exists():
                    logger.warning(f"    Target session directory {target_session_dir.name} already exists. Skipping move for {item.name}. Manual check might be needed.")
                else:
                    try:
                        shutil.move(str(item), str(target_session_dir))
                        logger.info(f"    Moved session dir {session_id} -> {target_session_dir.relative_to(DATA_DIR)}")
                    except Exception as e:
                        logger.error(f"    Error moving session directory {item.name}: {e}", exc_info=True)

        # 2b. Process loose files remaining in 'chats' directory
        logger.info(f"  Checking for loose files in {old_chats_dir}...")
        loose_files = [f for f in old_chats_dir.iterdir() if f.is_file() and f.suffix == '.json']

        for loose_file in loose_files:
            filename = loose_file.name
            session_id = None
            target_filename = None
            moved = False

            context_match = re.match(r"context_([0-9a-fA-F-]+)\.json", filename)
            timestamp_match = re.match(r"(\d{8}_\d{6})\.json", filename)

            if context_match:
                session_id = context_match.group(1)
                target_filename = "context.json"
                logger.info(f"    Found loose context file: {filename}")
                moved = move_file_to_session_dir(loose_file, user_dir, session_id, target_filename)
            elif timestamp_match:
                session_id = timestamp_match.group(1) # Use timestamp as session ID
                target_filename = "transcript.json"
                logger.info(f"    Found loose timestamp transcript file: {filename}")
                moved = move_file_to_session_dir(loose_file, user_dir, session_id, target_filename)
            else:
                logger.warning(f"    Skipping unrecognized loose file: {filename}")

        # 2c. Cleanup: Remove old 'chats' directory if it's empty
        try:
            # Check again if it exists and is empty
            if old_chats_dir.is_dir() and not any(old_chats_dir.iterdir()):
                old_chats_dir.rmdir()
                logger.info(f"  Removed empty 'chats' directory: {old_chats_dir}")
            elif old_chats_dir.is_dir():
                 logger.warning(f"  'chats' directory {old_chats_dir} is not empty after migration. Manual check needed.")
        except OSError as e:
            logger.error(f"  Error removing 'chats' directory {old_chats_dir}: {e}", exc_info=True)

    # 3. Cleanup: Remove old 'memory' directory (facts are now in DB)
    try:
        if old_memory_dir.is_dir():
            # Double check it's empty or only contains files we expect to delete
            items_left = list(old_memory_dir.iterdir())
            can_delete = True
            for item in items_left:
                # Add conditions here if some files should *not* be deleted
                # For now, assume we want to delete the whole dir if facts migrated
                pass
            if can_delete:
                 shutil.rmtree(old_memory_dir)
                 logger.info(f"  Removed 'memory' directory: {old_memory_dir}")
            else:
                 logger.warning(f"  'memory' directory {old_memory_dir} contains unexpected files. Manual check needed.")

    except OSError as e:
        logger.error(f"  Error removing 'memory' directory {old_memory_dir}: {e}", exc_info=True)


def main():
    """Main function to iterate through users and migrate files."""
    logger.info("Starting chat file migration (v3 - DB Facts)...")

    user_dirs = [d for d in DATA_DIR.iterdir() if d.is_dir() and d.name.isdigit()]

    if not user_dirs:
        logger.info("No user directories (numeric names) found to process.")
        return

    logger.info(f"Found {len(user_dirs)} potential user directories to process.")

    for user_dir in user_dirs:
        migrate_user_data(user_dir)

    logger.info("Chat file migration (v3) completed.")

if __name__ == "__main__":
    main()