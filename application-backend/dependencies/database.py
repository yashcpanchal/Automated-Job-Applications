import pymongo
from pymongo.database import Database
from core.config import MONGODB_URI, DATABASE_NAME
from typing import Annotated
from fastapi import Depends

# Iniitalizes the client globally
client = None

# Helper method to get mongo client
def get_mongo_client():
    global client
    if client is not None:
        if not MONGODB_URI:
            print("MONGODB URI NOT FOUND")
        client = pymongo.MongoClient(MONGODB_URI)
        print("Mongo connection established")
    return client

# closes mongo connection
def close_mongo_connection():
    global client
    if client:
        client.close()
        print("Mongo connection closed")

# Helper method to get the MongoDB instance
def get_database():
    client = get_mongo_client()
    db = client[DATABASE_NAME]
    return db

DatabaseDependency = Annotated[Database, Depends(get_database)]
