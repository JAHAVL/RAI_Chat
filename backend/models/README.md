# Models Directory

This directory contains SQLAlchemy ORM models that define database tables for the RAI Chat application.

## Directory Structure

- `__init__.py` - Initializes the SQLAlchemy Base class and imports all models
- `connection.py` - Database connection management
- `user.py` - User table definition (authentication and user information)
- `session.py` - Chat session table definition
- `message.py` - Message table definition for storing chat messages
- `system_message.py` - System message table definition for storing system notifications

## Important Note on Models vs. Managers

In this application, there's a clear separation of concerns:

1. **Models (this directory):** SQLAlchemy database models that define table structure and relationships.
2. **Managers (/managers):** Business logic classes that operate on models and provide higher-level functionality.

For example:
- `models/session.py` defines the database table structure for chat sessions
- `managers/user_session_manager.py` provides business logic for managing those sessions

## Model Relationships

- `User` has many `Session`s (one-to-many)
- `Session` belongs to a `User` (many-to-one)
- `Session` has many `Message`s (one-to-many)
- `Message` belongs to a `Session` (many-to-one)
- `SystemMessage` belongs to a `Session` (many-to-one)
