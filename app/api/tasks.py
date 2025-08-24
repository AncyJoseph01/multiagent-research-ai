from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime
from sqlalchemy import insert, select, update, delete

from app.db.database import database
from app.db import models
from app.schema.task import Task, TaskCreate

router = APIRouter()


# Create a new task
@router.post("/", response_model=Task)
async def create_task(task: TaskCreate):
    # Check if the user exists
    query = select(models.User).where(models.User.id == task.user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    task_id = uuid.uuid4()
    query = insert(models.Task).values(
        id=task_id,
        description=task.description,
        due_date=task.due_date,
        status=task.status or "pending",
        created_at=datetime.utcnow(),
        user_id=task.user_id,
    )
    await database.execute(query)

    return Task(
        id=task_id,
        description=task.description,
        due_date=task.due_date,
        status=task.status or "pending",
        created_at=datetime.utcnow(),
        user_id=task.user_id,
    )


# Get all tasks
@router.get("/", response_model=List[Task])
async def read_tasks():
    query = select(models.Task)
    rows = await database.fetch_all(query)
    return rows


# Get a task by ID
@router.get("/{task_id}", response_model=Task)
async def read_task(task_id: uuid.UUID):
    query = select(models.Task).where(models.Task.id == task_id)
    task = await database.fetch_one(query)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# Update a task
@router.put("/{task_id}", response_model=Task)
async def update_task(task_id: uuid.UUID, updated_task: TaskCreate):
    # Check if the task exists
    query = select(models.Task).where(models.Task.id == task_id)
    task = await database.fetch_one(query)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if the user exists
    query = select(models.User).where(models.User.id == updated_task.user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = (
        update(models.Task)
        .where(models.Task.id == task_id)
        .values(
            description=updated_task.description,
            due_date=updated_task.due_date,
            status=updated_task.status or "pending",
            user_id=updated_task.user_id,
        )
    )
    await database.execute(q)

    return Task(
        id=task_id,
        description=updated_task.description,
        due_date=updated_task.due_date,
        status=updated_task.status or "pending",
        created_at=task["created_at"],
        user_id=updated_task.user_id,
    )


# Delete a task
@router.delete("/{task_id}")
async def delete_task(task_id: uuid.UUID):
    query = select(models.Task).where(models.Task.id == task_id)
    task = await database.fetch_one(query)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    q = delete(models.Task).where(models.Task.id == task_id)
    await database.execute(q)

    return {"message": "Task deleted successfully"}
