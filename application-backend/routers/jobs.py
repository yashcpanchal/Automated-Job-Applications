from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel, Field
from services.job_search import JobSearchService
from typing import List, Dict, Any, Optional
from models.job import Job
from dependencies.database import get_database, get_mongo_client
from dependencies.embedding_model import get_embedding_model
from datetime import datetime
import uuid
from dependencies.redis import get_redis
import redis.asyncio as aioredis
import json
import logging
from bson import ObjectId
from core.config import TEST_COLLECTION
from auth import get_current_user, UserInDB

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    user_id: Optional[str] = None

# Paginated Reponse class
class PaginatedResponse(BaseModel):
    items: List[Job]
    total: int
    page: int
    page_size: int
    total_pages: int


def serialize_datetime(obj):
    """Custom serializer for datetime and binary data."""
    try:
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        if isinstance(obj, BaseModel):
            result = {}
            for field_name, field_value in obj.model_dump().items():
                if isinstance(field_value, bytes):
                    result[field_name] = base64.b64encode(field_value).decode('utf-8')
                else:
                    result[field_name] = field_value
            return result
        
        if isinstance(obj, bytes):
            encoded = base64.b64encode(obj).decode('utf-8')
            return encoded
        
        raise TypeError(f"Type {type(obj)} not serializable")
    except Exception as e:
        raise

async def save_task_status(
    redis_client: aioredis.Redis,
    task_id: str,
    status: str, 
    status_message: str,
    error: Optional[str] = None,
    result: Optional[List[Job]] = None,
    result_summary: Optional[str] = None,
    user_id: Optional[str] = None
):
    now = datetime.now()
    task_status = {
        "task_id": task_id,
        "status": status,
        "status_message": status_message,
        "created_at": now.isoformat(),
        "completed_at": None,
        "error": error,
        "result": result,
        "user_id": user_id
    }

    if status in ["completed", "failed"]:
        task_status["completed_at"] = now.isoformat()
    
    try:
        # First convert all objects to serializable types
        serialized_result = []
        if result:
            for job in result:
                if hasattr(job, 'model_dump'):
                    serialized_result.append(json.loads(job.model_json()))
                else:
                    serialized_result.append(job)
        
        task_status["result"] = serialized_result
        
        # Now serialize the entire task status
        task_status_json = json.dumps(task_status, default=serialize_datetime, ensure_ascii=False)
        
        await redis_client.set(
            f"task:{task_id}",
            task_status_json,
            ex=TASK_TTL
        )
    except Exception as e:
        print(f"Error saving task status: {e}")
        # Fallback to a minimal error status if serialization fails
        error_status = {
            "task_id": task_id,
            "status": "failed",
            "status_message": "Error processing task",
            "error": str(e),
            "created_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "user_id": user_id
        }
        await redis_client.set(
            f"task:{task_id}",
            json.dumps(error_status, default=serialize_datetime, ensure_ascii=False),
            ex=TASK_TTL
        )
    return task_status
    
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
    if hasattr(obj, 'model_dump_json'):
        try:
            return json.loads(obj.model_dump_json())
        except:
            pass
    if hasattr(obj, 'dict'):
        try:
            return sanitize_for_json(obj.dict())
        except:
            pass
    if hasattr(obj, '__dict__'):
        try:
            return sanitize_for_json(obj.__dict__)
        except:
            pass
    try:
        return str(obj)
    except:
        return "[unserializable object]"


@router.post("/agent-search", response_model=JobSearchStatus)
async def agent_search(
    request: JobSearchRequest,
    background_tasks: BackgroundTasks,
    redis_client: aioredis.Redis = Depends(get_redis),
    db = Depends(get_database),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Start job search with agent, done in background.
    Adjust the task status using Redis
    """
    task_id = str(uuid.uuid4())

    user_id_for_search = current_user.id

    # Create a sanitized task data
    task_data = {
        "task_id": task_id,
        "status_message": "Task started",
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "user_id": user_id_for_search
    }

    # Save initial task status with sanitized data
    try:
        serialized_data = json.dumps(task_data, default=str, ensure_ascii=False)
        await redis_client.set(
            f"task:{task_id}",
            serialized_data,
            ex=TASK_TTL
        )
    except Exception as e:
        # Fallback to basic data if serialization fails
        fallback_data = {
            "task_id": task_id,
            "status": "pending",
            "status_message": "Task started",
            "error": "Initial serialization warning: " + str(e),
            "user_id": user_id_for_search
        }
        await redis_client.set(
            f"task:{task_id}",
            json.dumps(fallback_data, ensure_ascii=False),
            ex=TASK_TTL
        )

    async def run_search(
        db_client: Any,
        embedding_model_instance: Any,
        redis_client: aioredis.Redis,
        task_id: str,
        resume_text: str,
        search_prompt: str,
        request: JobSearchRequest,
        user_id: str
    ) -> None:
        try:
            # Run the search with the original text inputs
            job_search_service = JobSearchService()
            final_jobs: List[Job] = await job_search_service.search_and_process_jobs(
                user_id=user_id,
                resume_text=resume_text,
                search_prompt=search_prompt
            )
            
            # Save final jobs to the database - simplified version
            jobs_to_save = []
            for job in final_jobs:
                job_dict = job.model_dump()
                job_dict["user_id"] = user_id
                # Ensure all values are JSON serializable
                job_dict = {k: sanitize_for_json(v) for k, v in job_dict.items()}
                jobs_to_save.append(job_dict)
            
            if jobs_to_save:
                inserted = await db_client.jobs.insert_many(jobs_to_save)
                logger.info(f"Inserted {len(inserted.inserted_ids)} jobs into the database")
        
            # Prepare result for Redis with proper error handling
            try:
                result = []
                for job in final_jobs:
                    try:
                        job_dict = job.model_dump()
                        result.append(sanitize_for_json(job_dict))
                    except Exception as e:
                        result.append({"error": f"Failed to process job data: {str(e)}"})
                
                # Create response data
                response_data = {
                    "task_id": task_id,
                    "status": "completed",
                    "status_message": "Task complete!",
                    "created_at": datetime.now().isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "result": result,
                    "user_id": user_id
                }
                
                # Ensure final serialization works
                try:
                    serialized = json.dumps(response_data, default=str, ensure_ascii=False)
                    await redis_client.set(
                        f"task:{task_id}",
                        serialized,
                        ex=TASK_TTL
                    )
                except Exception as e:
                    await redis_client.set(
                        f"task:{task_id}",
                        json.dumps({
                            "task_id": task_id,
                            "status": "completed",
                            "status_message": "Task completed but some data could not be serialized",
                            "result_count": len(result)
                        }, ensure_ascii=False),
                        ex=TASK_TTL
                    )
            except Exception as e:
                await redis_client.set(
                    f"task:{task_id}",
                    json.dumps({
                        "task_id": task_id,
                        "status": "error",
                        "error": f"Failed to process results: {str(e)}",
                        "created_at": datetime.now().isoformat(),
                        "user_id": user_id
                    }, ensure_ascii=False),
                    ex=TASK_TTL
                )
            
        except Exception as e:
            error_msg = str(e)
            try:
                error_data = {
                    "task_id": task_id,
                    "status": "failed",
                    "status_message": "Task failed!",
                    "error": error_msg,
                    "created_at": datetime.now().isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "user_id": user_id
                }
                await redis_client.set(
                    f"task:{task_id}",
                    json.dumps(error_data, ensure_ascii=False),
                    ex=TASK_TTL
                )
            except Exception as inner_e:
                try:
                    await redis_client.set(
                        f"task:{task_id}",
                        '{"status":"error","message":"Critical error occurred"}',
                        ex=TASK_TTL
                    )
                except:
                    pass  # If we can't even save this, there's nothing more we can do
    # Get the embedding model instance
    model = get_embedding_model()
    
    # Run the search in the background
    background_tasks.add_task(
        run_search,
        db_client=db,
        embedding_model_instance=model,
        redis_client=redis_client,
        task_id=task_id,
        resume_text=request.resume_text,
        search_prompt=request.search_prompt,
        request=request,
        user_id=user_id_for_search
    )

    # Return the sanitized task data
    return task_data

# GET endpoint to get the status of a task
@router.get("/task-status/{task_id}", response_model=JobSearchStatus)
async def get_task_status(task_id: str, redis_client: aioredis.Redis = Depends(get_redis), current_user: UserInDB = Depends(get_current_user)):
    """
    Get the status of a job search task.
    """
    task_data = await redis_client.get(f"task:{task_id}")
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if json.loads(task_data)["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        return json.loads(task_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid task data format")
    return task_data


# GET endpoint to retrieve matched jobs
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
    user_id: str,
    db = Depends(get_database),
    page: int = 1,
    page_size: int = 10,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Endpoint to retrieve matched jobs for a user.
    """
    try:
        user_id_for_search = current_user.id
        
        # Calculate skip value
        skip = (page - 1) * page_size
        
        # Get total count
        total = await db[TEST_COLLECTION].count_documents({"user_id": user_id_for_search})
        
        # Get paginated jobs
        cursor = db[TEST_COLLECTION].find({"user_id": user_id_for_search}) \
                             .sort("created_at", -1) \
                             .skip(skip) \
                             .limit(page_size)
        
        # Convert cursor to list of documents
        jobs = []
        async for doc in cursor:
            jobs.append(convert_mongo_doc(doc))
        
        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "items": jobs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
        
    except Exception as e:
        logger.error(f"Error retrieving matched jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving matched jobs: {str(e)}"
        )