# jobs.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel, Field
from services.job_search import JobSearchService
from typing import List, Dict, Any, Optional
from models.job import Job
from dependencies.database import get_database
from dependencies.embedding_model import get_embedding_model
from datetime import datetime
import uuid
from dependencies.redis import get_redis
import redis.asyncio as aioredis
import json
import logging
from routers.auth import UserInDB, get_current_user # Corrected import based on auth.py structure

router = APIRouter(
    prefix="/jobs",
    tags=["Job Search"]
)

TASK_TTL = 60 * 60 * 24  # 1 day


class JobSearchRequest(BaseModel):
    resume_text: str = Field(..., description="The user's resume represented as a string of text.")
    search_prompt: str = Field(..., description="Search prompt to guide the job search and ranking process.")

class JobSearchStatus(BaseModel):
    task_id: str
    status_message: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[List[Job]] = None
    progress: int = Field(0, ge=0, le=100, description="Progress of the job search task in percentage (0-100).")
    user_id: Optional[str] = None # Ensure this is Optional[str]

# Paginated Reponse class
class PaginatedResponse(BaseModel):
    items: List[Job]
    total: int
    page: int
    page_size: int
    total_pages: int


def serialize_datetime(obj):
    """Custom serializer for datetime objects to ISO format."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    # You might need to add specific handling for other non-standard types if your Job model
    # or other data structures contain them, but be precise.
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

async def update_redis_task_status(
    redis_client: aioredis.Redis,
    task_id: str,
    user_id: str, # Ensure user_id is passed and used
    status_message: str,
    progress: int = 0,
    result: Optional[List[Job]] = None,
    error: Optional[str] = None
):
    """
    Update the status of a task in Redis.
    """
    current_time = datetime.utcnow() # Use UTC for consistency
    
    # Fetch existing task data to update it, rather than overwriting completely
    existing_task_data_json = await redis_client.get(f"task:{task_id}")
    if existing_task_data_json:
        existing_task_data = json.loads(existing_task_data_json)
        # Preserve created_at if updating an existing task
        created_at = existing_task_data.get("created_at", current_time.isoformat())
    else:
        created_at = current_time.isoformat()


    task_data = {
        "task_id": task_id,
        "status_message": status_message,
        "created_at": created_at,
        "completed_at": None,
        "user_id": user_id, # <--- This is correctly set from the passed user_id string
        "progress": progress,
        "error": error, # Include error directly
        "result": None # Initialize result to None
    }

    if result is not None:
        # Ensure result jobs are properly serialized
        task_data["result"] = [job.model_dump() for job in result]
        task_data["completed_at"] = current_time.isoformat()
        task_data["progress"] = 100  # Mark as complete

    # Ensure error is explicitly set if provided
    if error:
        task_data["completed_at"] = current_time.isoformat()
        task_data["progress"] = 100
    
    try:
        # Use serialize_datetime as default for json.dumps if any datetime objects are present within nested structures
        await redis_client.setex(f"task:{task_id}", TASK_TTL, json.dumps(task_data, default=serialize_datetime))
    except Exception as e:
        logging.error(f"Failed to update task status in Redis for task {task_id}: {str(e)}", exc_info=True)
        # You might want to raise an HTTPException here or handle this more gracefully
        # For now, let's just log and let the main task handler deal with the failure
        raise


# Initiates a JSON santization process to ensure all data is JSON serializable
def sanitize_for_json(obj):
    """Recursively sanitize data to ensure it's JSON serializable."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(item) for item in obj]
    if isinstance(obj, bytes):
        # For bytes, return a placeholder or empty string
        return "[binary data]"
    if hasattr(obj, 'model_dump'): # Use model_dump for Pydantic v2
        try:
            return sanitize_for_json(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, 'dict'): # For Pydantic v1 compatibility
        try:
            return sanitize_for_json(obj.dict())
        except Exception:
            pass
    if hasattr(obj, '__dict__'):
        try:
            return sanitize_for_json(obj.__dict__)
        except Exception:
            pass
    if isinstance(obj, datetime): # Ensure datetime is handled if it reaches here
        return obj.isoformat()
    try:
        return str(obj)
    except Exception:
        return "[unserializable object]"

@router.post("/agent-search", response_model=JobSearchStatus)
async def agent_search(
    request: JobSearchRequest,
    background_tasks: BackgroundTasks,
    redis_client: aioredis.Redis = Depends(get_redis),
    db = Depends(get_database),
    embedding_model = Depends(get_embedding_model),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Start job search with agent, done in background.
    Adjust the task status using Redis
    """
    task_id = str(uuid.uuid4())
    user_id_str = str(current_user.id) # Convert ObjectId to string here

    # 1. Directly create JobSearchStatus for initial save
    initial_task_status = JobSearchStatus(
        task_id=task_id,
        status_message="Task initiated.",
        created_at=datetime.utcnow(),
        progress=0,
        user_id=user_id_str # Ensure user_id is set as a string here
    )

    # Store initial task status in Redis
    # Use .model_dump() to get a dictionary from the Pydantic model
    await redis_client.setex(
        f"task:{task_id}",
        TASK_TTL,
        json.dumps(initial_task_status.model_dump(), default=serialize_datetime)
    )

    async def run_search(
        db_client: Any,
        embedding_model_instance: Any,
        redis_client: aioredis.Redis,
        task_id: str,
        resume_text: str,
        search_prompt: str,
        user_id_for_task: str # This will be the string user ID
    ):
        try:
            await update_redis_task_status(
                redis_client=redis_client,
                task_id=task_id,
                user_id=user_id_for_task, # Use this consistently
                status_message="Searching for jobs...",
                progress=10
            )

            job_search_service = JobSearchService()
            
            final_jobs: List[Job] = await job_search_service.search_and_process_jobs(
                user_id=user_id_for_task,
                resume_text=resume_text,
                search_prompt=search_prompt
            )

            await update_redis_task_status(
                redis_client=redis_client,
                task_id=task_id,
                user_id=user_id_for_task,
                status_message="Processing results...",
                progress=50
            )
            
            # Save final jobs to the database
            jobs_to_save = []
            for job in final_jobs:
                job_dict = job.model_dump()
                job_dict["user_id"] = user_id_for_task
                job_dict["task_id"] = task_id  # Associate the job with the task ID
                job_dict["search_prompt_used"] = search_prompt  # Store the search prompt used
                job_dict["resume_text_hash"] = hash(resume_text)  # Store a hash of the resume text for reference
                # Ensure all values are JSON serializable
                job_dict = {k: sanitize_for_json(v) for k, v in job_dict.items()}
                jobs_to_save.append(job_dict)
            
            if jobs_to_save:
                # Assuming 'jobs' collection exists and db_client is your MongoDB database object
                inserted = await db_client.jobs.insert_many(jobs_to_save)
                print(f"Inserted {len(inserted.inserted_ids)} jobs into the database")
            
            await update_redis_task_status(
                redis_client=redis_client,
                task_id=task_id,
                user_id=user_id_for_task,
                status_message="Task complete!",
                result=final_jobs, # Pass the list of Job models
                progress=100
            )
        
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error in background task for task {task_id}: {error_msg}", exc_info=True)
            await update_redis_task_status(
                redis_client=redis_client,
                task_id=task_id,
                user_id=user_id_for_task, # Ensure user_id is passed even on error
                status_message="Task failed!",
                error=error_msg,
                progress=100
            )
            
    # Run the search in the background
    background_tasks.add_task(
        run_search,
        db_client=db,
        embedding_model_instance=embedding_model, # Use the dependency-injected model instance
        redis_client=redis_client,
        task_id=task_id,
        resume_text=request.resume_text,
        search_prompt=request.search_prompt,
        user_id_for_task=user_id_str # Pass the string user ID to the background task
    )

    # Return the initial task status object immediately
    return initial_task_status

# GET endpoint to retrieve matched jobs (no changes needed for this part, as the user did not specify issues here)
def convert_mongo_doc(doc):
    """Convert MongoDB document to a dictionary with proper serialization."""
    if not doc:
        return doc
    doc_dict = dict(doc)
    # Convert ObjectId to string
    if '_id' in doc_dict:
        doc_dict['_id'] = str(doc_dict['_id'])
    return doc_dict

@router.get("/matched-jobs", response_model=PaginatedResponse)
async def get_matched_jobs(
    db = Depends(get_database),
    page: int = 1,
    page_size: int = 10,
    current_user: UserInDB = Depends(get_current_user), # Get user_id from authenticated user
    task_id: Optional[str] = None # Optional task_id
):
    """
    Endpoint to retrieve matched jobs for the authenticated user.
    """
    try:
        user_id_str = str(current_user.id) # Use the ID from the authenticated user

        query = {"user_id": user_id_str}
        if task_id:
            query["task_id"] = task_id  # Filter by task_id if provided

        skip = (page - 1) * page_size
        total = await db.jobs.count_documents(query) # Filter by authenticated user's ID
        
        cursor = db.jobs.find(query).skip(skip).limit(page_size)
        jobs = []
        async for job in cursor:
            jobs.append(convert_mongo_doc(job))
        jobs_items = []
        for job_data in jobs:
            try:
                jobs_items.append(Job(**job_data))
            except Exception as e:
                print(f"Error converting job document to Job model: {e}")   
                
        return PaginatedResponse(
            items=jobs_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
    except Exception as e:
        error_detail = str(e)
        raise HTTPException(status_code=500, detail=error_detail)