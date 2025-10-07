from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from typing import Optional
from app.models.analytics import EndpointUsageCreate
from app.utils.helpers import logger, log_api_call

router = APIRouter()

@router.get("/daily", tags=["analytics"])
async def get_daily_endpoint_usage(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze (default: 7)"),
    db: Session = Depends(get_db)
):
    """
    Get endpoint usage per day for the last N days
    
    Returns:
    - Daily breakdown of endpoint hits
    - Each day shows which endpoints were hit and how many times
    """
    try:
        log_api_call("/analytics/daily", f"days={days}")
        
        analytics_service = AnalyticsService(db)
        daily_usage = analytics_service.get_daily_endpoint_usage(db, days=days)
        
        return {
            "success": True,
            "message": f"Daily endpoint usage for last {days} days",
            "data": daily_usage,
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting daily endpoint usage: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get daily endpoint usage: {str(e)}"
        )

@router.get("/weekly", tags=["analytics"])
async def get_weekly_endpoint_usage(
    weeks: int = Query(1, ge=1, le=12, description="Number of weeks to analyze (default: 1)"),
    db: Session = Depends(get_db)
):
    """
    Get endpoint usage per week for the last N weeks
    
    Returns:
    - Weekly breakdown of endpoint hits
    - Each week shows which endpoints were hit and how many times
    """
    try:
        log_api_call("/analytics/weekly", f"weeks={weeks}")
        
        analytics_service = AnalyticsService(db)
        weekly_usage = analytics_service.get_weekly_endpoint_usage(db, weeks=weeks)
        
        return {
            "success": True,
            "message": f"Weekly endpoint usage for last {weeks} weeks",
            "data": weekly_usage,
            "period_weeks": weeks
        }
        
    except Exception as e:
        logger.error(f"Error getting weekly endpoint usage: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get weekly endpoint usage: {str(e)}"
        )

@router.get("/monthly", tags=["analytics"])
async def get_monthly_overall_usage(
    months: int = Query(12, ge=1, le=24, description="Number of months to analyze (default: 12)"),
    db: Session = Depends(get_db)
):
    """
    Get overall endpoint usage per month for the last N months
    
    Returns:
    - Monthly breakdown of total hits and unique endpoints
    - Overall usage trends over time
    """
    try:
        log_api_call("/analytics/monthly", f"months={months}")
        
        analytics_service = AnalyticsService(db)
        monthly_usage = analytics_service.get_monthly_endpoint_usage(db, months=months)
        
        return {
            "success": True,
            "message": f"Monthly overall usage for last {months} months",
            "data": monthly_usage,
            "period_months": months
        }
        
    except Exception as e:
        logger.error(f"Error getting monthly overall usage: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get monthly overall usage: {str(e)}"
        )

@router.post("/track", tags=["analytics"])
async def track_endpoint_usage(
    usage_data: EndpointUsageCreate,
    db: Session = Depends(get_db)
):
    """
    Track endpoint usage manually (for testing or external tracking)
    
    This endpoint allows manual tracking of endpoint usage
    """
    try:
        log_api_call("/analytics/track", f"endpoint={usage_data.endpoint_path}")
        
        analytics_service = AnalyticsService(db)
        tracked_usage = analytics_service.track_endpoint_usage(usage_data)
        
        return {
            "success": True,
            "message": "Endpoint usage tracked successfully",
            "data": {
                "id": tracked_usage.id,
                "endpoint_path": tracked_usage.endpoint_path,
                "method": tracked_usage.method,
                "created_at": tracked_usage.created_at
            }
        }
        
    except Exception as e:
        logger.error(f"Error tracking endpoint usage: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track endpoint usage: {str(e)}"
        )


@router.get("/external-summary", tags=["analytics"])
async def get_external_api_summary(
    hours: int = Query(24, ge=1, le=168, description="Lookback window in hours (default: 24)"),
    db: Session = Depends(get_db)
):
    """
    Summarize external API usage (QDRANT, OPENAI, SERPAPI, TAVILY) over the lookback window.
    """
    try:
        from app.utils.helpers import log_api_call
        log_api_call("/analytics/external-summary", f"hours={hours}")

        analytics_service = AnalyticsService(db)
        summaries = analytics_service.summarize_external_usage(since_hours=hours)
        return {
            "success": True,
            "message": "External API usage summary",
            "data": [s.model_dump() for s in summaries]
        }
    except Exception as e:
        logger.error(f"Error getting external API summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get external API summary: {str(e)}"
        )
