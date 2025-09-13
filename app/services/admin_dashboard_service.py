from sqlalchemy.orm import Session
from app.services.allowed_url_service import AllowedUrlService
from app.services.chat_restriction_service import ChatRestrictionService
from app.services.analytics_service import AnalyticsService
from app.utils.helpers import logger
from typing import Dict, Any, List
import asyncio

class AdminDashboardService:
    """
    Service for consolidating all admin dashboard data into a single response
    """
    
    def __init__(self):
        # Services will be initialized with db session when needed
        pass
    
    async def get_all_dashboard_data(self, db: Session) -> Dict[str, Any]:
        """
        Get all admin dashboard data in a single call
        
        Returns:
            Dict containing all dashboard data:
            - chat_restrictions: List of chat restrictions
            - allowed_urls: List of allowed URLs
            - daily_analytics: Daily usage analytics (7 days)
            - weekly_analytics: Weekly usage analytics (4 weeks)
            - monthly_analytics: Monthly usage analytics (12 months)
        """
        try:
            logger.info("🚀 Starting consolidated admin dashboard data fetch")
            start_time = asyncio.get_event_loop().time()
            
            # Fetch all data concurrently for better performance
            results = await asyncio.gather(
                self._get_chat_restrictions(db),
                self._get_allowed_urls(db),
                self._get_daily_analytics(db),
                self._get_weekly_analytics(db),
                self._get_monthly_analytics(db),
                return_exceptions=True
            )
            
            # Process results
            chat_restrictions = results[0] if not isinstance(results[0], Exception) else []
            allowed_urls = results[1] if not isinstance(results[1], Exception) else []
            daily_analytics = results[2] if not isinstance(results[2], Exception) else []
            weekly_analytics = results[3] if not isinstance(results[3], Exception) else []
            monthly_analytics = results[4] if not isinstance(results[4], Exception) else []
            
            # Log any errors that occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_names = ["chat_restrictions", "allowed_urls", "daily_analytics", "weekly_analytics", "monthly_analytics"]
                    logger.error(f"❌ Error fetching {error_names[i]}: {str(result)}")
            
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ Consolidated admin dashboard data fetched in {duration:.2f}s")
            
            return {
                "chat_restrictions": chat_restrictions,
                "allowed_urls": allowed_urls,
                "daily_analytics": daily_analytics,
                "weekly_analytics": weekly_analytics,
                "monthly_analytics": monthly_analytics,
                "metadata": {
                    "fetch_time": duration,
                    "timestamp": asyncio.get_event_loop().time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in get_all_dashboard_data: {str(e)}")
            raise e
    
    async def _get_chat_restrictions(self, db: Session) -> List[Dict[str, Any]]:
        """Get chat restrictions data"""
        try:
            chat_service = ChatRestrictionService(db)
            restrictions = chat_service.get_all_chat_restrictions(skip=0, limit=100)
            return [{"restriction_text": r.restriction_text, "created_at": r.created_at} for r in restrictions]
        except Exception as e:
            logger.error(f"Error fetching chat restrictions: {e}")
            return []
    
    async def _get_allowed_urls(self, db: Session) -> List[Dict[str, Any]]:
        """Get allowed URLs data"""
        try:
            url_service = AllowedUrlService(db)
            urls = url_service.get_all_allowed_urls(skip=0, limit=100)
            return [{"url": u.url, "created_at": u.created_at} for u in urls]
        except Exception as e:
            logger.error(f"Error fetching allowed URLs: {e}")
            return []
    
    async def _get_daily_analytics(self, db: Session) -> List[Dict[str, Any]]:
        """Get daily analytics data (7 days)"""
        try:
            analytics_service = AnalyticsService(db)
            analytics = analytics_service.get_daily_endpoint_usage(db, days=7)
            return analytics
        except Exception as e:
            logger.error(f"Error fetching daily analytics: {e}")
            return []
    
    async def _get_weekly_analytics(self, db: Session) -> List[Dict[str, Any]]:
        """Get weekly analytics data (4 weeks)"""
        try:
            analytics_service = AnalyticsService(db)
            analytics = analytics_service.get_weekly_endpoint_usage(db, weeks=4)
            return analytics
        except Exception as e:
            logger.error(f"Error fetching weekly analytics: {e}")
            return []
    
    async def _get_monthly_analytics(self, db: Session) -> List[Dict[str, Any]]:
        """Get monthly analytics data (12 months)"""
        try:
            analytics_service = AnalyticsService(db)
            analytics = analytics_service.get_monthly_endpoint_usage(db, months=12)
            return analytics
        except Exception as e:
            logger.error(f"Error fetching monthly analytics: {e}")
            return []
