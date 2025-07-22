from pydantic import BaseModel, Field
from typing import List

class FilteredUrls(BaseModel):
    """
    A model to hold a list of filtered URLs that are likely job postings.
    """
    job_urls: List[str] = Field(..., description="A list of URLs that are likely job postings.")