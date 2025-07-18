from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from core.config import MONGODB_URI, DATABASE_NAME
import logging

logger = logging.getLogger(__name__)

# Initialize the client
client: Optional[AsyncIOMotorClient] = None

async def get_mongo_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance."""
    global client
    if client is None:
        try:
            if not MONGODB_URI:
                raise ValueError("MONGODB_URI is not set in environment variables")
                
            # Create a new async client
            client = AsyncIOMotorClient(MONGODB_URI)
            logger.info("Successfully created async MongoDB client")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create MongoDB client: {e}")
            raise
    
    return client

async def get_database():
    """Get database instance with connection test."""
    try:
        client = await get_mongo_client()
        # Test the connection
        await client.admin.command('ping')
        db = client[DATABASE_NAME]
        logger.info("Successfully connected to MongoDB")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
