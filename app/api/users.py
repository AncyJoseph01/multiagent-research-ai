from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime

from app.db.database import database
from app.db import models
from app.schema.user import User, UserCreate
from sqlalchemy import insert, select, update, delete
from fastapi import Form

router = APIRouter() 

# Create a new user
@router.post("/", response_model=User)
async def create_user(user: UserCreate):
    
    normalized_email = user.email.lower()

    
    query = select(models.User).where(models.User.email.ilike(normalized_email))
    existing_user = await database.fetch_one(query)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = uuid.uuid4()
    query = insert(models.User).values(
        id=user_id,
        email=normalized_email,  # store lowercase
        name=user.name,
        created_at=datetime.utcnow()
    )
    await database.execute(query)

    return User(id=user_id, email=normalized_email, name=user.name, created_at=datetime.utcnow())



# Get all users
@router.get("/", response_model=List[User])
async def read_users():
    query = select(models.User)
    rows = await database.fetch_all(query)
    return rows


# Get a user by ID
@router.get("/{user_id}", response_model=User)
async def read_user(user_id: uuid.UUID):
    query = select(models.User).where(models.User.id == user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Update a user
@router.put("/{user_id}", response_model=User)
async def update_user(user_id: uuid.UUID, updated_user: UserCreate):
    query = select(models.User).where(models.User.id == user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = (
        update(models.User)
        .where(models.User.id == user_id)
        .values(email=updated_user.email, name=updated_user.name)
    )
    await database.execute(q)

    return User(id=user_id, email=updated_user.email, name=updated_user.name, created_at=user["created_at"])


# Delete a user
@router.delete("/{user_id}")
async def delete_user(user_id: uuid.UUID):
    query = select(models.User).where(models.User.id == user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = delete(models.User).where(models.User.id == user_id)
    await database.execute(q)

    return {"message": "User deleted successfully"}

@router.post("/login", response_model=User)
async def login_user(email: str = Form(...)):
    normalized_email = email.lower()
    query = select(models.User).where(models.User.email.ilike(normalized_email))
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
