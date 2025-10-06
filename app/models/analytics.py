from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class EndpointUsage(Base):
    """Model to track endpoint usage analytics"""
    __tablename__ = "endpoint_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    endpoint_path = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    response_status = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Integer, nullable=True)
    request_size_bytes = Column(Integer, nullable=True)
    response_size_bytes = Column(Integer, nullable=True)
    additional_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class EndpointUsageCreate(BaseModel):
    """Schema for creating endpoint usage records"""
    endpoint_path: str
    method: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    response_status: int
    response_time_ms: Optional[int] = None
    request_size_bytes: Optional[int] = None
    response_size_bytes: Optional[int] = None
    additional_data: Optional[Dict[str, Any]] = None

class EndpointUsageResponse(BaseModel):
    """Schema for endpoint usage responses"""
    id: int
    endpoint_path: str
    method: str
    user_agent: Optional[str]
    ip_address: Optional[str]
    response_status: int
    response_time_ms: Optional[int]
    request_size_bytes: Optional[int]
    response_size_bytes: Optional[int]
    additional_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ExternalApiUsage(Base):
    """Model to track external API usage (QDRANT, OPENAI, SERPAPI, TAVILY)"""
    __tablename__ = "external_api_usage"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)  # qdrant|openai|serpapi|tavily
    operation = Column(String(100), nullable=True)  # e.g., search_peptides, embeddings.create, search, chat.completions
    status_code = Column(Integer, nullable=True)
    success = Column(Integer, nullable=False, default=1)  # 1 true, 0 false
    latency_ms = Column(Integer, nullable=True)
    request_bytes = Column(Integer, nullable=True)
    response_bytes = Column(Integer, nullable=True)
    meta = Column('metadata', JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ExternalApiUsageCreate(BaseModel):
    provider: str
    operation: Optional[str] = None
    status_code: Optional[int] = None
    success: bool = True
    latency_ms: Optional[int] = None
    request_bytes: Optional[int] = None
    response_bytes: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ExternalApiUsageSummary(BaseModel):
    provider: str
    total_calls: int
    successes: int
    failures: int
    avg_latency_ms: Optional[float] = None