import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Date, Integer
from sqlalchemy.dialects.postgresql import UUID 
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import UniqueConstraint
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    papers = relationship("Paper", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)




class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (UniqueConstraint("user_id", "arxiv_id", name="unique_user_arxiv"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    authors = Column(Text)
    arxiv_id = Column(String, nullable=True)  # remove unique=True
    url = Column(Text, nullable=True)
    published_at = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="papers")
    summaries = relationship("Summary", back_populates="paper", cascade="all, delete-orphan", passive_deletes=True)
    embeddings = relationship("Embedding", back_populates="paper", cascade="all, delete-orphan", passive_deletes=True)



class Summary(Base):
    __tablename__ = "summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    summary_type = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"))
    paper = relationship("Paper", back_populates="summaries")


class Chat(Base):
    __tablename__ = "chat"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_session_id = Column(Integer, nullable=False, index=True) 
    query = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    cot_transcript = Column(Text, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="chats")




class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(Integer, nullable=True)
    vector = Column(Vector(768))
    created_at = Column(DateTime, default=datetime.utcnow)

    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"))
    paper = relationship("Paper", back_populates="embeddings")
