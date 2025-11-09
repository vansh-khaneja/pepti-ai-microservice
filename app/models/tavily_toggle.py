from sqlalchemy import Column, Boolean, DateTime, String
from sqlalchemy.sql import func
from app.core.database import Base
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# SQLAlchemy Model
class TavilyToggle(Base):
    __tablename__ = "tavily_toggle"
    
    id = Column(String, primary_key=True, default="main")  # Single row with id="main"
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# Pydantic Models for API
class TavilyToggleUpdate(BaseModel):
    """Model for updating Tavily search toggle"""
    enabled: bool = Field(..., description="Enable or disable Tavily search")

class TavilyToggleSchema(BaseModel):
    """Complete model for Tavily toggle response"""
    id: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TavilyToggleResponse(BaseModel):
    """Response model for Tavily toggle operations"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[TavilyToggleSchema] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

