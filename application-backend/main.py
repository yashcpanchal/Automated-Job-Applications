from fastapi import FastAPI, Depends
from typing import Optional, Annotated # We'll use this later for optional secrets
import pymongo
import os
from dotenv import load_dotenv

app = FastAPI()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "job_applications_bot_db"
COLLECTION_NAME = "classified_records"

def get_database():
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    try:
        yield db
    finally:
        client.close()

DatabaseDependency = Annotated[pymongo.database.Database, Depends(get_database)]

@app.get("/")
def message(db: DatabaseDependency, question: Optional[str]):
    if question:
        if "hello" in question.lower():
            message = "user says hello edited!"
            db[COLLECTION_NAME].insert_one({"message": message})
        else:
            message = "Message sent to db and received"
            db[COLLECTION_NAME].insert_one({"message": message})
    return {"secret_message": message}