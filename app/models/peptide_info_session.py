from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from typing import Optional
import uuid

class PeptideInfoSession(Base):
    """Model for peptide info generation sessions"""
    __tablename__ = "peptide_info_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=True)  # Optional user identification
    peptide_name = Column(String(200), nullable=False)  # The peptide being researched
    requirements = Column(Text, nullable=True)  # Specific requirements for the info
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    title = Column(String(200), nullable=True)  # Optional session title
    
    # Relationship to messages
    messages = relationship("PeptideInfoMessage", back_populates="session", cascade="all, delete-orphan")

class PeptideInfoMessage(Base):
    """Model for individual peptide info generation messages"""
    __tablename__ = "peptide_info_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    msg_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("peptide_info_sessions.session_id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    query = Column(Text, nullable=True)  # User query (for assistant messages)
    response = Column(Text, nullable=True)  # Assistant response (for assistant messages)
    content = Column(Text, nullable=False)  # General content field (for user messages)
    source = Column(String(50), nullable=True)  # 'tavily', 'tavily+tuned', 'serpapi', 'serpapi+tuned'
    accuracy_score = Column(Float, nullable=True)  # Accuracy score from Tavily or similarity score
    source_content = Column(Text, nullable=True)  # Raw content from the source
    source_urls = Column(JSON, nullable=True)  # URLs used as sources
    meta = Column('metadata', JSON, nullable=True, default={})  # Additional metadata as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to session
    session = relationship("PeptideInfoSession", back_populates="messages")
