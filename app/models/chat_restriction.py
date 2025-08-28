from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# SQLAlchemy Model
class ChatRestriction(Base):
    __tablename__ = "chat_restrictions"
    
    restriction_text = Column(Text, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Pydantic Models for API
class ChatRestrictionCreate(BaseModel):
    """Model for creating a new chat restriction"""
    restriction_text: str = Field(..., min_length=1, max_length=1000, description="The restriction text to be enforced")



class ChatRestrictionSchema(BaseModel):
    """Complete model for chat restriction response"""
    restriction_text: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatRestrictionResponse(BaseModel):
    """Response model for chat restriction operations"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[ChatRestrictionSchema] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRestrictionListResponse(BaseModel):
    """Response model for listing chat restrictions"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: list[ChatRestrictionSchema] = []
    total: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
