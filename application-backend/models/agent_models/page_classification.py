from pydantic import BaseModel, Field
from typing import Literal

class PageClassification(BaseModel):
    """
    The classification of the webpage content.
    - JOB_DESCRIPTION: The page is a detailed description of a single job.
    - JOB_BOARD: The page is a list of multiple job postings.
    - IRRELEVANT: The page is not a job posting (e.g., a blog post, company homepage).
    """
    classification: Literal["JOB_DESCRIPTION", "JOB_BOARD", "IRRELEVANT"] = Field(
        ...,
        description="The classification of the webpage content."
    )

class ExtractedPageClassification(BaseModel):
    """
    The classification of the webpage content.
    - JOB_DESCRIPTION: The page is a detailed description of a single job.
    - IRRELEVANT: The page is not a job posting (e.g., a blog post, company homepage).
    """
    classification: Literal["JOB_DESCRIPTION", "IRRELEVANT"] = Field(
        ...,
        description="The classification of the webpage content."
    )
