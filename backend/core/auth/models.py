# RAI_Chat/Backend/core/auth/models.py
# Docker-specific version with simplified schema

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserSchema(BaseModel):
    """Pydantic schema for user data representation within the application."""
    user_id: int
    username: str
    crm_user_id: Optional[str] = None

    class Config:
        # Allows Pydantic models to be created from ORM objects directly
        from_attributes = True # For Pydantic V2+
        orm_mode = True  # For backward compatibility with Pydantic V1

# Example Schema for user creation (might be used in API input validation)
class UserCreateSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6) # Password received plain, will be hashed

# Example Schema for user login
class UserLoginSchema(BaseModel):
    username: str
    password: str
