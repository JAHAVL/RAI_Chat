# RAI_Chat/backend/api/__init__.py

# Remove the automatic imports to prevent circular imports
# The blueprints will be imported directly in app.py

# Export the expected blueprint names as documentation
__all__ = ['auth_bp', 'chat_bp', 'memory_bp', 'session_bp']
