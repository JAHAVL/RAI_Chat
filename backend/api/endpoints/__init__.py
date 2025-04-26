# RAI_Chat_V2/backend/api/endpoints/__init__.py

"""
Frontend-facing API endpoints for RAI Chat

This package previously contained individual Flask blueprints that defined HTTP endpoints
for the frontend to communicate with the backend. These have now been consolidated into
a single centralized API handler (frontend_api_handler.py).

This directory is maintained for compatibility and may contain test endpoints.
"""

# No longer exporting individual blueprint names since they've been consolidated
__all__ = []
