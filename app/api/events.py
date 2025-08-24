from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime
from sqlalchemy import insert, select, update, delete

from app.db.database import database
from app.db import models
from app.schema.event import Event, EventCreate

router = APIRouter()


# Create a new event
@router.post("/", response_model=Event)
async def create_event(event: EventCreate):
    # Check if the user exists
    query = select(models.User).where(models.User.id == event.user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    event_id = uuid.uuid4()
    query = insert(models.Event).values(
        id=event_id,
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        external_id=event.external_id,
        created_at=datetime.utcnow(),
        user_id=event.user_id,
    )
    await database.execute(query)

    return Event(
        id=event_id,
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        external_id=event.external_id,
        created_at=datetime.utcnow(),
        user_id=event.user_id,
    )


# Get all events
@router.get("/", response_model=List[Event])
async def read_events():
    query = select(models.Event)
    rows = await database.fetch_all(query)
    return rows


# Get an event by ID
@router.get("/{event_id}", response_model=Event)
async def read_event(event_id: uuid.UUID):
    query = select(models.Event).where(models.Event.id == event_id)
    event = await database.fetch_one(query)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


# Update an event
@router.put("/{event_id}", response_model=Event)
async def update_event(event_id: uuid.UUID, updated_event: EventCreate):
    # Check if the event exists
    query = select(models.Event).where(models.Event.id == event_id)
    event = await database.fetch_one(query)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if the user exists
    query = select(models.User).where(models.User.id == updated_event.user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    q = (
        update(models.Event)
        .where(models.Event.id == event_id)
        .values(
            title=updated_event.title,
            description=updated_event.description,
            start_time=updated_event.start_time,
            end_time=updated_event.end_time,
            external_id=updated_event.external_id,
            user_id=updated_event.user_id,
        )
    )
    await database.execute(q)

    return Event(
        id=event_id,
        title=updated_event.title,
        description=updated_event.description,
        start_time=updated_event.start_time,
        end_time=updated_event.end_time,
        external_id=updated_event.external_id,
        created_at=event["created_at"],
        user_id=updated_event.user_id,
    )


# Delete an event
@router.delete("/{event_id}")
async def delete_event(event_id: uuid.UUID):
    query = select(models.Event).where(models.Event.id == event_id)
    event = await database.fetch_one(query)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    q = delete(models.Event).where(models.Event.id == event_id)
    await database.execute(q)

    return {"message": "Event deleted successfully"}
