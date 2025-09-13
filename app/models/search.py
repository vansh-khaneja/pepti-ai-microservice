from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchRequest(BaseModel):
    """Model for search request"""
    peptide_name: str = Field(..., min_length=1, max_length=100, description="Name of the peptide to search for")
    requirements: str = Field(..., min_length=1, max_length=500, description="Specific requirements or characteristics to search for")

class SearchResult(BaseModel):
    """Model for individual search result"""
    title: str
    url: str
    snippet: str
    rank: int

class ContentChunk(BaseModel):
    """Model for content chunk"""
    content: str
    source_url: str
    chunk_index: int
    relevance_score: Optional[float] = None
    confidence_score: Optional[float] = Field(None, description="Confidence score as percentage (0-100)")

class SourceSite(BaseModel):
    """Model for source site information"""
    title: str
    url: str
    similarity_score: Optional[float] = Field(None, description="Relevance score for this source (0-1)")
    content_length: Optional[int] = Field(None, description="Length of scraped content from this source")

class SearchResponse(BaseModel):
    """Model for search response"""
    peptide_name: str
    requirements: str
    generated_response: str
    source_sites: List[SourceSite]
    search_timestamp: datetime

class SearchAPIResponse(BaseModel):
    """API response wrapper"""
    success: bool = True
    message: str = "Search completed successfully"
    data: Optional[SearchResponse] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
