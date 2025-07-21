# auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List, Any
from jose import JWTError, jwt
from bson import ObjectId

from dependencies.database import get_database
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, USER_COLLECTION

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Custom Pydantic Type for MongoDB ObjectId
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, field: Any = None) -> ObjectId: # Corrected signature for Pydantic validator
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema) -> None:
        field_schema.update(type="string")

    model_config = ConfigDict(json_encoders={ObjectId: str})

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# --- Pydantic Models (Corrected) ---

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class UserInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    username: str
    hashed_password: str
    full_name: Optional[str] = None
    resume_embedding: Optional[List[float]] = None
    prompt_embedding: Optional[List[float]] = None
    saved_job_ids: List[str] = Field(default_factory=list, description="A list of Job IDs that the user has saved.")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

class UserOut(BaseModel):
    # This model is for public responses, hence no hashed_password
    id: str = Field(alias="_id")
    username: str = Field(...) # <--- THIS IS THE CRITICAL CHANGE: It must be 'username', not 'user'
    full_name: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )

    @classmethod
    def from_user_in_db(cls, user_db: UserInDB) -> 'UserOut':
        """Helper to create UserOut instance from UserInDB."""
        return cls(
            id=str(user_db.id),
            username=user_db.username, # <--- Ensure this is setting the 'username' field
            full_name=user_db.full_name
        )

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- End Pydantic Models ---

# Password Hashing Helper Functions
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_user(db: AsyncIOMotorDatabase, username: str, password: str) -> Optional[UserInDB]:
    user_data = await db[USER_COLLECTION].find_one({"username": username})
    if not user_data:
        return None
    if not verify_password(password, user_data["hashed_password"]):
        return None
    return UserInDB(**user_data)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(
    db: AsyncIOMotorDatabase = Depends(get_database),
    token: str = Depends(oauth2_scheme)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(f"DEBUG: Token received in get_current_user: {token[:20]}...")
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print(f"DEBUG: Decoded payload: {payload}")
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        print(f"DEBUG: JWT Error during decoding: {e}")
        raise credentials_exception

    user_data = await db[USER_COLLECTION].find_one({"username": token_data.username})
    if user_data is None:
        raise credentials_exception
    return UserInDB(**user_data)

# FastAPI Authentication Endpoints
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data_in: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if await db[USER_COLLECTION].find_one({"username": user_data_in.username}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    hashed_password = get_password_hash(user_data_in.password)

    user_to_insert = UserInDB(username=user_data_in.username, hashed_password=hashed_password)

    try:
        result = await db[USER_COLLECTION].insert_one(user_to_insert.model_dump(by_alias=True, exclude_none=True))

        created_user_doc = await db[USER_COLLECTION].find_one({"_id": result.inserted_id})

        if not created_user_doc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve created user")

        user_in_db_instance = UserInDB(**created_user_doc)

        return UserOut.from_user_in_db(user_in_db_instance)

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Data validation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Registration failed due to an internal error: {str(e)}")


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate a new access token for the user upon login
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=JWT_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return UserOut.from_user_in_db(current_user)