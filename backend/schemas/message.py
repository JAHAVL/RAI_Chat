# RAI_Chat/backend/schemas/message.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class MessageSchema(BaseModel):
    """Pydantic schema for message data representation."""
    message_id: str
    session_id: str
    user_id: int
    role: str  # 'user' or 'assistant'
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class MessageCreateSchema(BaseModel):
    """Schema for creating a new message."""
    content: str = Field(..., min_length=1)
    role: str = Field(..., pattern='^(user|assistant)$')
    metadata: Optional[Dict[str, Any]] = None


class MessageListSchema(BaseModel):
    """Schema for returning a list of messages."""
    messages: List[MessageSchema]
