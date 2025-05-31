from fastapi import FastAPI, Depends
from typing import Optional, Annotated # These are used for type hinting
from datetime import datetime # Used for timestamp 
import pymongo
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

app = FastAPI()

# loads the .env file
load_dotenv()

# Mongo vars
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "job-application-bot-db"
COLLECTION_NAME = "resume-embeddings"

# Embedding model
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

def get_database():
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    try:
        yield db
    finally:
        client.close()

DatabaseDependency = Annotated[pymongo.database.Database, Depends(get_database)]

@app.get("/")
def test(db: DatabaseDependency, question: Optional[str]):
    try:
        if question:
            message = "Message sent to db and received"
            db[COLLECTION_NAME].insert_one({"message": message})
        return {"message": message}
    except Exception as e:
        return {"error": f"Something went wrong {str(e)}"}


# Pass in txt of resume and other relevant information and embed it
@app.post("/embed-text/")
def embed_resume_text(data: dict, db: DatabaseDependency):
    text_input = data.get("text")
    print(text_input)
    try:
        if text_input:
            print("start embedding calculations")
            embedding_vector = embedding_model.encode(text_input).tolist()
            print(embedding_vector)
            print("end embedding calculations")
            db[COLLECTION_NAME].insert_one({
                "embedding": embedding_vector,
                "text": text_input,
                "timestamp": datetime.now()
            })
        return {"data": data.get("text")}
    except Exception as e:
        return {"error": f"Something went wrong {str(e)}"}