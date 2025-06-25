from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Job(BaseModel):
    title: str
    employment_type: str
    company_name: str
    country: str
    state: Optional[str] = None
    job_description: str
    url: str
    date_posted: Optional[datetime] = None
