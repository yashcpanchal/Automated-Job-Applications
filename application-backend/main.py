import logging
import json
import base64
from typing import Any
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from routers import auth, pdf, jobs
from core.config import MONGODB_URI, JSEARCH_API_KEY
from dependencies.database import get_mongo_client
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Custom JSON encoder
def custom_json_encoder(obj: Any) -> Any:
    """Custom JSON encoder that handles binary data."""
    try:
        if isinstance(obj, bytes):
            logger.debug(f"Encoding bytes object of length {len(obj)}")
            return base64.b64encode(obj).decode('utf-8')
        return json.JSONEncoder.default(obj)
    except Exception as e:
        logger.error(f"Error in custom_json_encoder: {str(e)}")
        raise

# Custom JSONable encoder
def custom_jsonable_encoder(obj: Any) -> Any:
    """Custom JSON encoder that handles binary data in errors."""
    try:
        if isinstance(obj, bytes):
            logger.debug(f"Encoding bytes object in error: {obj[:50]}")
            return base64.b64encode(obj).decode('utf-8')
        if isinstance(obj, ValidationError):
            logger.debug(f"Processing ValidationError with {len(obj.errors())} errors")
            return obj.errors()
        return obj
    except Exception as e:
        logger.error(f"Error in custom_jsonable_encoder: {str(e)}")
        raise

app = FastAPI(
    title="Job Applications Bot API",
    description="API for job applications bot",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Job Search",
            "description": "Operations related to job search"
        }
    ]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_mongo_client()
        print("MongoDB client initialized successfully.")
    except Exception as e:
        print("Error, failed to initialize MongoDB client: {e}")
    yield
    await close_mongo_connection()

# app.include_router(job.router)
# app.include_router(user.router)
# app.include_router(apply.router)
app.include_router(pdf.router)
app.include_router(jobs.router)



@app.get("/")
def read_root():
    return {"message": "Welcome to the Job Applications Bot API! Check /docs for endpoints."}