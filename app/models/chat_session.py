from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from typing import Optional
import uuid

class ChatSession(Base):
    """Model for chat sessions"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=True)  # Optional user identification
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    title = Column(String(200), nullable=True)  # Optional session title
    
    # Relationship to messages
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    """Model for individual chat messages"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    msg_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.session_id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    query = Column(Text, nullable=True)  # User query (for assistant messages)
    response = Column(Text, nullable=True)  # Assistant response (for assistant messages)
    content = Column(Text, nullable=False)  # General content field (for user messages)
    source = Column(String(50), nullable=True)  # 'qdrant', 'qdrant+judge', 'tavily'
    score = Column(Float, nullable=True)  # Similarity score or average Tavily score
    # Use attribute name 'meta' to avoid SQLAlchemy reserved name 'metadata'
    meta = Column('metadata', JSON, nullable=True, default={})  # Additional metadata as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to session
    session = relationship("ChatSession", back_populates="messages")
