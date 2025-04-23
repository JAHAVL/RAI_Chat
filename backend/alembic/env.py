import sys # Added
from pathlib import Path # Added
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- Add project root to sys.path ---
try:
    # Assumes env.py is in alembic directory, which is in Backend directory
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    print(f"env.py: Added project root to sys.path: {PROJECT_ROOT}") # Use print for visibility during migration
except Exception as e:
     print(f"env.py: Error adding project root to sys.path: {e}")
     # Decide if we should exit; for now, let it potentially fail later
# --- End sys.path modification ---

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Import Base from your models module
from RAI_Chat.backend.core.database.models import Base
target_metadata = Base.metadata
# target_metadata = None # Original line commented out

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Get URL from alembic.ini or environment variable via context config
    db_url = context.config.get_main_option("sqlalchemy.url")
    if not db_url:
        # Fallback or raise error if URL is crucial and not found
        import os
        db_url = os.environ.get("DATABASE_URL")
        # Use the default SQLite path if still not found
        if not db_url:
             # Construct the default path relative to PROJECT_ROOT defined earlier
             DEFAULT_DB_PATH = PROJECT_ROOT / 'RAI_Chat' / 'Backend' / 'core' / 'database' / 'temp_dev.db'
             db_url = f"sqlite:///{DEFAULT_DB_PATH}"
             print(f"env.py: WARNING - Using default DB URL: {db_url}")
             # Ensure the directory exists for SQLite
             try:
                 DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
             except OSError as e:
                 print(f"env.py: ERROR - Failed to create directory for default SQLite DB: {e}")
                 # Decide if we should raise an error here

    # Configure context for offline mode
    context.configure(
        url=db_url, # Use the determined URL
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Import create_engine
from sqlalchemy import create_engine
import os # Ensure os is imported if not already

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Determine DB URL: Prioritize DATABASE_URL environment variable for online mode
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fallback to alembic.ini setting if env var is not set
        db_url = context.config.get_main_option("sqlalchemy.url")
        if not db_url:
            # Final fallback to default SQLite path
            DEFAULT_DB_PATH = PROJECT_ROOT / 'RAI_Chat' / 'Backend' / 'core' / 'database' / 'temp_dev.db'
            db_url = f"sqlite:///{DEFAULT_DB_PATH}"
            print(f"env.py: WARNING - Using default DB URL for online mode: {db_url}")
            # Ensure the directory exists for SQLite
            try:
                DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                print(f"env.py: ERROR - Failed to create directory for default SQLite DB: {e}")
                # Decide if we should raise an error here
    else:
        print(f"env.py: Using DATABASE_URL from environment for online mode: {db_url}")

    # Create engine directly
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    # Original engine_from_config call removed:
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    with connectable.connect() as connection:
        # Pass include_schemas=True if using schemas with SQLite or other backends
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # include_schemas=True # Uncomment if needed, e.g., for PostgreSQL schemas
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
