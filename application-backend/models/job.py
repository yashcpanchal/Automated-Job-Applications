from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
import uuid

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
    source_url: str = Field(..., description="The original URL where the job listing was found.")
    score: Optional[float] = Field(None, description="The ranking score of the job based on similarities to the user's resume and prompt.")
    
    class Config:
        # This allows us to use `_id` as the field name in MongoDB but `id` in our Pydantic model
        populate_by_name = True
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