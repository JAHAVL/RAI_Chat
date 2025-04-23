# RAI_Chat/Backend/core/auth/models.py

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

# Example Schema for user creation (might be used in API input validation)
class UserCreateSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: str = Field(..., min_length=6) # Password received plain, will be hashed

# Example Schema for user login
class UserLoginSchema(BaseModel):
    username: str
    password: str