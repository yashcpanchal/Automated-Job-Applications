from fastapi import APIRouter
from dependencies.database import DatabaseDependency
from dependencies.embedding_model import ModelDependency
from core.config import USER_COLLECTION
from datetime import datetime

router = APIRouter(
    prefix="/user-input",
    tags=["Input resume and prompt"]
)

# To do in the future: Function to take in resume text and prompt
# To do in the future: setup in json schema in models and replace dict with the new schema
# To do in the future: add in logic to check if a username already exists and do an upsert operation on that

# Takes in text of prompt, embeds it, and writes it to database
@router.post("/embed-text")
def embed_resume_text(data: dict, db: DatabaseDependency,
                       embedding_model: ModelDependency):
    text_input = data.get("text")
    username = data.get("username")
    try:
        if db[USER_COLLECTION].find_one("username", username):
            if text_input:
                embedding_vector = embedding_model.encode(text_input).tolist()
                db[USER_COLLECTION].insert_one({
                    "username": username,
                    "embedding": embedding_vector,
                    "text": text_input,
                    "timestamp": datetime.now()
                })
            return {"data": data.get("text")}
    except Exception as e:
        return {"error": f"Something went wrong {str(e)}"}
