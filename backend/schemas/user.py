# RAI_Chat/backend/schemas/user.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserSchema(BaseModel):
    """Pydantic schema for user data representation within the application."""
    user_id: int
    username: str
    email: Optional[EmailStr] = None
    crm_user_id: Optional[str] = None
    auth_provider: str = 'local'
    is_active: bool = True
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        # Allows Pydantic models to be created from ORM objects directly
        # Deprecated in Pydantic V2, use `from_attributes = True` instead
        # orm_mode = True # For Pydantic V1
        from_attributes = True # For Pydantic V2+


class UserCreateSchema(BaseModel):
    """Schema for user creation (used in API input validation)."""
    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=6) # Password received plain, will be hashed


class UserLoginSchema(BaseModel):
    """Schema for user login."""
    username: str
    password: str
