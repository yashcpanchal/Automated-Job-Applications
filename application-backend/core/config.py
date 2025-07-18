import os
from dotenv import load_dotenv

load_dotenv()

# Mongo vars
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "job-application-bot-db"
USER_COLLECTION = "user-data-collection"
JOB_DATA_COLLECTION = "job-data"
TEST_COLLECTION = "test-collection"

# Jsearch API
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
JSEARCH_API_HOST = os.getenv("JSEARCH_API_HOST")

# Embedding model
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

# Gemini API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Brave SERP API
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

if not MONGODB_URI:
    print("MONGODB_URI NOT FOUND")
if not JSEARCH_API_HOST:
    print("JSEARCH API HOST NOT FOUND")
if not JSEARCH_API_KEY:
    print("JSEARCH API KEY NOT FOUND")
if not GOOGLE_API_KEY:
    print("GOOGLE API KEY NOT FOUND")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


