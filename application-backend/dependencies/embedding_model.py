from sentence_transformers import SentenceTransformer
from core.config import EMBEDDING_MODEL_NAME
from typing import Annotated
from fastapi import Depends

embedding_model_instance = None

def get_embedding_model():
    global embedding_model_instance
    if embedding_model_instance is None:
        embedding_model_instance = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return embedding_model_instance

ModelDependency = Annotated[SentenceTransformer, Depends(get_embedding_model)]