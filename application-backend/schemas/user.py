from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    """
    Model for creating a new user. This is what the user will send to the
    /users/ endpoint.
    """
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    full_name: Optional[str] = None
    # Will add more later
    
    # For swagger ui
    class Config:
        json_schema_extra = {
            "example": {
                "email": "testuser@example.com",
                "password": "StrongPassword123!",
                "full_name": "Test User"
            }
        }
