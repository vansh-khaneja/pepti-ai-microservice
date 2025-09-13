from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.admin_dashboard_service import AdminDashboardService
from app.utils.helpers import log_api_call
from typing import Dict, Any

router = APIRouter()

@router.get("/admin-dashboard", response_model=Dict[str, Any], tags=["admin-dashboard"])
async def get_admin_dashboard_data(
    db: Session = Depends(get_db)
):
    """
    Get all admin dashboard data in a single API call
    
    This endpoint consolidates all the data needed for the admin dashboard:
    - Chat restrictions
    - Allowed URLs
    - Daily analytics (7 days)
    - Weekly analytics (4 weeks)
    - Monthly analytics (12 months)
    
    This reduces the number of API calls from 4+ separate calls to just 1 call,
    significantly improving the initial loading time of the admin dashboard.
    """
    try:
        # Log the API call
        log_api_call("/admin-dashboard", "GET")
        
        # Initialize admin dashboard service
        admin_service = AdminDashboardService()
        
        # Get all dashboard data in one call
        dashboard_data = await admin_service.get_all_dashboard_data(db)
        
        return {
            "success": True,
            "message": "Admin dashboard data retrieved successfully",
            "data": dashboard_data
        }
        
    except Exception as e:
        # Log the error
        log_api_call("/admin-dashboard", "GET", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve admin dashboard data: {str(e)}"
        )
