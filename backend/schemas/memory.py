# RAI_Chat/backend/schemas/memory.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class MemoryItemSchema(BaseModel):
    """Pydantic schema for a memory item."""
    content: str
    created_at: datetime
    source: str = "user_explicit"  # 'user_explicit', 'system_inferred', etc.
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class UserMemorySchema(BaseModel):
    """Pydantic schema for a user's remembered facts."""
    user_id: int
    memories: List[MemoryItemSchema]
    last_updated: datetime

    class Config:
        from_attributes = True


class MemoryCreateSchema(BaseModel):
    """Schema for creating a new memory item."""
    content: str = Field(..., min_length=1)
    source: str = "user_explicit"
    metadata: Optional[Dict[str, Any]] = None


class MemorySearchSchema(BaseModel):
    """Schema for searching memory items."""
    query: str = Field(..., min_length=1)
    limit: int = 5
