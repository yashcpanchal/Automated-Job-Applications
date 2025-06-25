from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    email: str
    hashed_password: str # Make sure to hash the password before storing
    full_name: Optional[str] = None
    resume_embedding: Optional[List[float]] = None # Storing the vector from the user's resume
    saved_job_ids: List[str] = Field(default_factory=list, description="A list of Job IDs that the user has saved.")