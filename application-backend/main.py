from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from routers import job, user
from core.config import MONGODB_URI, JSEARCH_API_KEY
from dependencies.database import get_mongo_client, close_mongo_connection

app = FastAPI(
    title="Job Applications Bot API",
    description="Backend for automated job applications with AI",
    version="0.1.0",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        get_mongo_client()
        print("MongoDB client initialized successfully.")
    except Exception as e:
        print("Error, failed to initialize MongoDB client: {e}")
    yield
    close_mongo_connection()

app.include_router(job.router)
app.include_router(user.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Job Applications Bot API! Check /docs for endpoints."}