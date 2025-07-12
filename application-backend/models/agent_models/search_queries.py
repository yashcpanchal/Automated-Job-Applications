from pydantic import BaseModel, Field
from typing import List

class SearchQueries(BaseModel):
    """List of search queries to use."""
    queries: List[str] = Field(
        ...,
        description="""A list of 3-5 diverse, expert-level search engine queries to find job postings."""
    )
