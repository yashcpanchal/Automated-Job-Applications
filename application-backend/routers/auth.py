from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, validator, Field
from passlib.context import CryptContext
from datetime import datetime
from typing import Optional
from jose import JWTError, jwt
from dependencies.database import get_database
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from core.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, USER_COLLECTION
from bson import ObjectId

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# Pydantic Models
class UserInDB(BaseModel):
    id: Optional[str] = Field(alias="_id") # MongoDB ObjectId
    username: str
    hashed_password: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

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
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(db: AsyncIOMotorDatabase = Depends(get_database), token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = await db[USER_COLLECTION].find_one({"username": token_data.username})
    if user is None:
        raise credentials_exception
    return UserInDB(**user)

# FastAPI Authentication Endpoints
@router.post("/register", response_model=UserInDB, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    if await db[USER_COLLECTION].find_one({"username": user.username}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    
    hashed_password = get_password_hash(user.password)
    user_data = {
        "username": user.username,
        "hashed_password": hashed_password
    }
    # Insert user data into MongoDB
    await db[USER_COLLECTION].insert_one(user_data)
    return user

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Generate a new access token for the user upon login
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=JWT_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}
    
@router.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

