from fastapi import APIRouter, Depends, HTTPException
import json
import redis.asyncio as aioredis
from typing import Dict, Any

from routers.auth import UserInDB
from dependencies.redis import get_redis
from routers.auth import get_current_user
from routers.jobs import JobSearchStatus

router = APIRouter()

@router.get("/task-status/{task_id}", response_model=JobSearchStatus)
async def get_task_status(
    task_id: str, 
    redis_client: aioredis.Redis = Depends(get_redis), 
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get the status of a job search task.
    """
    print(f"[DEBUG] Getting task status for task_id: {task_id}")
    print(f"[DEBUG] Current user: {current_user.username} (ID: {current_user.id})")
    
    task_data = await redis_client.get(f"task:{task_id}")
    if not task_data:
        print(f"[DEBUG] Task {task_id} not found in Redis")
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        task_dict = json.loads(task_data)
        print(f"[DEBUG] Task data from Redis: {task_dict}")
        
        # Debug: Print types for comparison
        print(f"[DEBUG] Type of task_dict['user_id']: {type(task_dict.get('user_id'))}")
        print(f"[DEBUG] Type of current_user.id: {type(current_user.id)}")
        print(f"[DEBUG] Values - task user_id: {task_dict.get('user_id')}, current_user.id: {current_user.id}")
        
        # Check if this task belongs to the current user
        if str(task_dict.get("user_id")) != str(current_user.id):
            print("[DEBUG] Access denied - user ID mismatch")
            raise HTTPException(status_code=403, detail="Access denied")
        
        return task_dict
    except json.JSONDecodeError:
        print("[ERROR] Failed to decode task data from Redis")
        raise HTTPException(status_code=500, detail="Invalid task data format")