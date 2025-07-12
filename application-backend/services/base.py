from motor.motor_asyncio import AsyncIOMotorCollection
from typing import TypeVar, Generic, Type, List
from pydantic import BaseModel
from pymongo.results import InsertOneResult, UpdateResult

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseService(Generic[ModelType]):
    """
    Generic base service class with CRUD operations
    """
    def __init__(self, collection: AsyncIOMotorCollection, model: Type[ModelType]):
        """
        Initializes the service with a mongodb collection and a pydantic model

        :param collection: The asynchronous Motor collection from MongoDB.
        :param model: The Pydantic model class for data validation and shaping.
        """
        self.collection = collection
        self.model = model
    
    async def get(self, item_id: str):
        """Fetches a single item by id"""
        document = await self.collection.find_one({"id": item_id})
        if document:
            return self.model(**document)
        return None
    
    async def get_multiple(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Fetch multiple items from the database with pagination."""
        documents = await self.collection.find().skip(skip).limit(limit).to_list(length=limit)
        return [self.model(**doc) for doc in documents]
    
    async def create(self, data: BaseModel) -> InsertOneResult:
        """Create a new item in the database."""
        doc = data.model_dump(by_alias=True)
        result = await self.collection.insert_one(doc)
        return result

    async def update(self, item_id: str, data: BaseModel) -> UpdateResult:
        """Update an existing item in the database."""
        # Use $set to update only the provided fields
        update_data = data.model_dump(exclude_unset=True)
        result = await self.collection.update_one({"_id": item_id}, {"$set": update_data})
        return result

