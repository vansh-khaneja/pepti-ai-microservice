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
    - Server information (start time and uptime)
    
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
        
@router.get("/admin-dashboard/cost-analytics", response_model=Dict[str, Any], tags=["admin-dashboard"])
async def get_cost_analytics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get detailed cost analytics for admin dashboard
    
    This endpoint provides comprehensive cost analytics including:
    - Daily cost trends (last 7 days)
    - Weekly cost trends (last 4 weeks) 
    - Monthly cost trends (last 12 months)
    - Top costing services
    - Overall cost summary
    
    Args:
        days: Number of days for cost summary (default: 30)
    """
    try:
        # Log the API call
        log_api_call("/admin-dashboard/cost-analytics", "GET")
        
        # Initialize admin dashboard service
        admin_service = AdminDashboardService()
        
        # Get cost analytics data
        cost_data = await admin_service.get_cost_analytics_data(db, days)
        
        return {
            "success": True,
            "message": "Cost analytics data retrieved successfully",
            "data": cost_data
        }
        
    except Exception as e:
        # Log the error
        log_api_call("/admin-dashboard/cost-analytics", "GET", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve cost analytics data: {str(e)}"
        )

@router.get("/admin-dashboard/top-costing-services", response_model=Dict[str, Any], tags=["admin-dashboard"])
async def get_top_costing_services(
    limit: int = 10,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get top costing services for admin dashboard
    
    Args:
        limit: Number of top services to return (default: 10)
        days: Number of days to analyze (default: 30)
    """
    try:
        # Log the API call
        log_api_call("/admin-dashboard/top-costing-services", "GET")
        
        # Initialize analytics service
        from app.services.analytics_service import AnalyticsService
        analytics_service = AnalyticsService(db)
        
        # Get top costing services
        top_services = analytics_service.get_top_costing_services(db, limit=limit, days=days)
        
        return {
            "success": True,
            "message": "Top costing services retrieved successfully",
            "data": {
                "top_services": top_services,
                "period_days": days,
                "limit": limit
            }
        }
        
    except Exception as e:
        # Log the error
        log_api_call("/admin-dashboard/top-costing-services", "GET", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve top costing services: {str(e)}"
        )

@router.get("/admin-dashboard/cost-summary", response_model=Dict[str, Any], tags=["admin-dashboard"])
async def get_cost_summary(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive cost summary for admin dashboard
    
    Args:
        days: Number of days to analyze (default: 30)
    """
    try:
        # Log the API call
        log_api_call("/admin-dashboard/cost-summary", "GET")
        
        # Initialize analytics service
        from app.services.analytics_service import AnalyticsService
        analytics_service = AnalyticsService(db)
        
        # Get cost summary
        cost_summary = analytics_service.get_cost_summary(db, days=days)
        
        return {
            "success": True,
            "message": "Cost summary retrieved successfully",
            "data": cost_summary
        }
        
    except Exception as e:
        # Log the error
        log_api_call("/admin-dashboard/cost-summary", "GET", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve cost summary: {str(e)}"
        )
