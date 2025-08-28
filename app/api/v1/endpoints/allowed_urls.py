from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.services.allowed_url_service import AllowedUrlService
from app.core.database import get_db
from app.models.allowed_url import (
    AllowedUrl, 
    AllowedUrlCreate, 
    AllowedUrlResponse,
    AllowedUrlListResponse
)

router = APIRouter()

@router.post("/", response_model=AllowedUrlResponse, tags=["allowed-urls"])
def create_allowed_url(
    url_data: AllowedUrlCreate,
    db: Session = Depends(get_db)
):
    """Create a new allowed URL"""
    try:
        service = AllowedUrlService(db)
        created_url = service.create_allowed_url(url_data)
        return AllowedUrlResponse(
            success=True,
            message="Allowed URL created successfully",
            data=created_url
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/", response_model=AllowedUrlListResponse, tags=["allowed-urls"])
def get_all_allowed_urls(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all allowed URLs with pagination"""
    try:
        service = AllowedUrlService(db)
        urls = service.get_all_allowed_urls(skip=skip, limit=limit)
        return AllowedUrlListResponse(
            success=True,
            message="Allowed URLs retrieved successfully",
            data=urls,
            total=len(urls)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.delete("/{url:path}", response_model=AllowedUrlResponse, tags=["allowed-urls"])
def delete_allowed_url(
    url: str,
    db: Session = Depends(get_db)
):
    """Delete an allowed URL"""
    try:
        service = AllowedUrlService(db)
        service.delete_allowed_url(url)
        return AllowedUrlResponse(
            success=True,
            message="Allowed URL deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))






