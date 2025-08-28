from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from app.services.chat_restriction_service import ChatRestrictionService
from app.core.database import get_db
from app.models.chat_restriction import (
    ChatRestrictionCreate,
    ChatRestrictionResponse,
    ChatRestrictionListResponse
)

router = APIRouter()

@router.post("/", response_model=ChatRestrictionResponse, tags=["chat-restrictions"])
def create_chat_restriction(
    restriction_data: ChatRestrictionCreate,
    db: Session = Depends(get_db)
):
    """Create a new chat restriction"""
    try:
        service = ChatRestrictionService(db)
        created_restriction = service.create_chat_restriction(restriction_data)
        return ChatRestrictionResponse(
            success=True,
            message="Chat restriction created successfully",
            data=created_restriction
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=ChatRestrictionListResponse, tags=["chat-restrictions"])
def get_all_chat_restrictions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all chat restrictions with pagination"""
    try:
        service = ChatRestrictionService(db)
        restrictions = service.get_all_chat_restrictions(skip=skip, limit=limit)
        total = service.get_total_count()
        return ChatRestrictionListResponse(
            success=True,
            message="Chat restrictions retrieved successfully",
            data=restrictions,
            total=total
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{restriction_text:path}", response_model=ChatRestrictionResponse, tags=["chat-restrictions"])
def delete_chat_restriction(
    restriction_text: str,
    db: Session = Depends(get_db)
):
    """Delete a chat restriction by its text"""
    try:
        service = ChatRestrictionService(db)
        service.delete_chat_restriction(restriction_text)
        return ChatRestrictionResponse(
            success=True,
            message="Chat restriction deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
