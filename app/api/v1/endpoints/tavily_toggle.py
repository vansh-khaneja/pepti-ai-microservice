from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services.tavily_toggle_service import TavilyToggleService
from app.core.database import get_db
from app.models.tavily_toggle import (
    TavilyToggleUpdate,
    TavilyToggleResponse
)

router = APIRouter()

@router.get("/", response_model=TavilyToggleResponse, tags=["tavily-toggle"])
def get_tavily_toggle(
    db: Session = Depends(get_db)
):
    """Get the current Tavily search toggle setting"""
    try:
        service = TavilyToggleService(db)
        toggle = service.get_tavily_toggle()
        return TavilyToggleResponse(
            success=True,
            message="Tavily toggle retrieved successfully",
            data=toggle
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/", response_model=TavilyToggleResponse, tags=["tavily-toggle"])
def update_tavily_toggle(
    toggle_data: TavilyToggleUpdate,
    db: Session = Depends(get_db)
):
    """Update the Tavily search toggle setting"""
    try:
        service = TavilyToggleService(db)
        updated_toggle = service.update_tavily_toggle(toggle_data)
        return TavilyToggleResponse(
            success=True,
            message=f"Tavily search {'enabled' if updated_toggle.enabled else 'disabled'} successfully",
            data=updated_toggle
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

