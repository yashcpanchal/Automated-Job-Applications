from core.config import TEST_COLLECTION
from models.job import Job
from dependencies.embedding_model import get_embedding_model
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime
from services.util.text_processing import preprocess_text

async def ingest_job_and_embed(job_data: dict, db: AsyncIOMotorDatabase):
    embedding_model = get_embedding_model()
    try:
        job = Job(**job_data)
    except Exception as e:
        print(f"Error creating Job instance: {e}")
        print(f"Job data that caused the error: {job_data}")
        raise

    # Preprocess the job description and title
    if job.description:
        job.description = preprocess_text(job.description)
    if job.title:
        job.title = preprocess_text(job.title)
    
    # Generate the embeddings if there is a description
    if job.description:
        job.description_embedding = embedding_model.encode(job.description).tolist()
    if job.title:
        job.title_embedding = embedding_model.encode(job.title).tolist()

    jobs_collection = db[TEST_COLLECTION]

    job_document = job.model_dump(by_alias=True, exclude_none=True, exclude={'id'})

    # Use the update_one method to update the job document
    await jobs_collection.update_one(
        {"source_url": job.source_url},
        {"$set": job_document},
        upsert=True
    )
