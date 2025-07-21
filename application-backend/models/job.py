from pydantic import BaseModel, Field, ConfigDict, field_validator, model_serializer
from typing import Optional, List, Any, Union, Dict, Any
import uuid
from bson import ObjectId
from datetime import datetime
import json

class Job(BaseModel):
    """
    Represents a single job listing which will be retrieved by the AI search agent.
    Will be stored in the 'job-data-collection' in the mongodb
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    title: str = Field(..., description="Official title of the job (e.g., 'intern')")
    company: str = Field(..., description="Name of the company hiring for this position")
    location: Optional[str] = Field(None, description="The physical location of the job (e.g., 'San Francisco, CA').")
    description: str = Field(..., description="The full job description text.")
    application_url: Optional[str] = Field(None, description="The direct URL to the application page for this job.")
    date_posted: Optional[str] = Field(None, description="The date the job was originally posted.")
    description_embedding: Optional[List[float]] = Field(None, description="Embedding of the job description text.")
    title_embedding: Optional[List[float]] = Field(None, description="Embedding for the job title.")
    source_url: str = Field(..., description="The original URL where the job listing was found.")
    user_id: Optional[str] = Field(None, description="The ID of the user who created the job listing.")
    @field_validator('user_id', mode='before')
    @classmethod
    def convert_user_id_to_string(cls, v):
        if v is None:
            return None
        if isinstance(v, ObjectId):
            return str(v)
        return v
    
    class Config:
        # This allows us to use `_id` as the field name in MongoDB but `id` in our Pydantic model
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: lambda v: str(v) if v else None
        }
    

    
    def update_embeddings(self, model: Any) -> None:
        """Update both title and description embeddings using the provided model."""
        if not self.title_embedding and self.title:
            self.title_embedding = model.encode(self.title).tolist()
        
        if not self.description_embedding and self.description:
            self.description_embedding = model.encode(self.description).tolist()
    
    @classmethod
    def from_dict(cls, data: dict, model: Any = None) -> 'Job':
        """Create a Job instance from a dictionary and optionally update embeddings."""
        job = cls(**data)
        if model:
            job.update_embeddings(model)
        return job
        # Example to show the model's schema in OpenAPI docs
        # json_schema_extra = {
        #     "example": {
        #         "title": "Senior Backend Engineer",
        #         "company": "Tech Solutions Inc.",
        #         "location": "Remote",
        #         "description": "Seeking a skilled backend engineer with experience in Python and cloud services...",
        #         "application_url": "https://apply.workable.com/tech-solutions/j/12345ABCDE/",
        #         "date_posted": "2023-10-27T10:00:00Z",
        #         "source_url": "https://www.linkedin.com/jobs/view/1234567890/"
        #     }
        # }
