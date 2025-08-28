from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

# SQLAlchemy Model
class AllowedUrl(Base):
    __tablename__ = "allowed_urls"
    
    url = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Pydantic Models for API
class AllowedUrlCreate(BaseModel):
    """Model for creating a new allowed URL"""
    url: str = Field(..., description="The URL or domain to be allowed (e.g., 'https://examine.com' or 'examine.com')")
    
    @validator('url')
    def format_url(cls, v):
        """Format URL to ensure it has protocol and is properly formatted"""
        if not v:
            raise ValueError('URL cannot be empty')
        
        # Remove any whitespace
        v = v.strip()
        
        # Check if it's a wildcard URL
        if '*' in v:
            # Handle special case: just "*" means allow any domain
            if v == '*':
                return '*'
            
            # For wildcard URLs, don't add protocol if it's just a domain
            if not v.startswith(('http://', 'https://')) and not v.startswith('*'):
                v = f'https://{v}'
            
            # Basic validation for wildcard URLs - allow shorter patterns
            if len(v) < 2:
                raise ValueError('Invalid wildcard URL format')
            return v
        
        # For regular URLs, add protocol if missing
        if not v.startswith(('http://', 'https://')):
            v = f'https://{v}'
        
        # Basic URL validation
        if not v or len(v) < 4:
            raise ValueError('Invalid URL format')
        
        return v

class AllowedUrlSchema(BaseModel):
    """Complete model for allowed URL response"""
    url: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class AllowedUrlResponse(BaseModel):
    """Response model for allowed URL operations"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[AllowedUrlSchema] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AllowedUrlListResponse(BaseModel):
    """Response model for listing allowed URLs"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: list[AllowedUrlSchema] = []
    total: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
