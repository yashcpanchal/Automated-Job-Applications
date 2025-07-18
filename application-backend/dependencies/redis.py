import redis.asyncio as redis
from fastapi import Depends
import json
from typing import Optional, Dict, Any, AsyncGenerator
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Get a Redis client instance."""
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield redis_client
    finally:
        await redis_client.close()