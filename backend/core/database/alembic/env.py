import os
import sys
from logging.config import fileConfig
from dotenv import load_dotenv # Import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import create_engine # Added for explicit engine creation if needed

from alembic import context

# Ensure the project root is in the Python path for imports
# Adjust this path if your alembic command is run from a different directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
# Load environment variables from .env file in the project root
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(DOTENV_PATH):
    print(f"Loading environment variables from: {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import your Base model - adjust the import path as necessary
from RAI_Chat.backend.core.database.models import Base
# Import the function to get the database URL from connection.py
# This centralizes the logic for getting the URL
from RAI_Chat.backend.core.database.connection import get_database_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None
target_metadata = Base.metadata # Point Alembic to your Base metadata

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
    # Use the centralized function to get the database URL
    # url = config.get_main_option("sqlalchemy.url") # Read from ini (commented out)
    url = get_database_url() # Get URL from environment/config via connection.py
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use the centralized function to get the database URL
    db_url = get_database_url()
    # Create engine explicitly using the URL from environment/config
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    # Original method using engine_from_config (less explicit about URL source):
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    #     url=db_url # Pass the URL explicitly if using engine_from_config
    # )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
