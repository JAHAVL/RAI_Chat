# RAI_Chat/backend/schemas/session.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class SessionSchema(BaseModel):
    """Pydantic schema for session data representation."""
    session_id: str
    user_id: int
    title: Optional[str] = None
    created_at: datetime
    last_activity_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to Pydantic model, handling JSON fields."""
        if hasattr(obj, 'metadata_json') and obj.metadata_json:
            # Create a copy of the object's attributes
            obj_dict = {c: getattr(obj, c) for c in obj.__table__.columns.keys()}
            # Replace metadata_json with metadata
            obj_dict['metadata'] = obj_dict.pop('metadata_json')
            return cls(**obj_dict)
        return super().from_orm(obj)


class SessionCreateSchema(BaseModel):
    """Schema for creating a new session."""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionUpdateSchema(BaseModel):
    """Schema for updating an existing session."""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionListSchema(BaseModel):
    """Schema for returning a list of sessions."""
    sessions: List[SessionSchema]
