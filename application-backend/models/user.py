from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from bson import ObjectId
import uuid

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    email: str
    hashed_password: str # Make sure to hash the password before storing
    full_name: Optional[str] = None
    resume_embedding: Optional[List[float]] = None # Storing the vector from the user's resume
    prompt_embedding: Optional[List[float]] = None # Storing the vector from the user's prompt
    saved_job_ids: List[str] = Field(default_factory=list, description="A list of Job IDs that the user has saved.")
    
    def update_resume_embedding(self, resume_text: str) -> None:
        """Update the resume embedding by parsing the resume text."""
        from services.pdf_processing.parse_resume import parse_resume
        _, embedding = parse_resume(resume_text)
        self.resume_embedding = embedding
    
    def update_prompt_embedding(self, prompt: str, model) -> None:
        """Update the prompt embedding using the provided model."""
        if not prompt:
            return
        self.prompt_embedding = model.encode(prompt).tolist()