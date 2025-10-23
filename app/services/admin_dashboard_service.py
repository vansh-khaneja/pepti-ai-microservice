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
                self._get_external_daily(db),
                self._get_external_weekly(db),
                self._get_external_api_summary(db),
                self._get_external_daily_cost(db),
                self._get_external_weekly_cost(db),
                self._get_external_monthly_cost(db),
                self._get_top_costing_services(db),
                self._get_cost_summary(db),
                return_exceptions=True
            )
            
            # Process results
            chat_restrictions = results[0] if not isinstance(results[0], Exception) else []
            allowed_urls = results[1] if not isinstance(results[1], Exception) else []
            external_daily = results[2] if not isinstance(results[2], Exception) else []
            external_weekly = results[3] if not isinstance(results[3], Exception) else []
            external_api_summary = results[4] if not isinstance(results[4], Exception) else []
            external_daily_cost = results[5] if not isinstance(results[5], Exception) else []
            external_weekly_cost = results[6] if not isinstance(results[6], Exception) else []
            external_monthly_cost = results[7] if not isinstance(results[7], Exception) else []
            top_costing_services = results[8] if not isinstance(results[8], Exception) else []
            cost_summary = results[9] if not isinstance(results[9], Exception) else {}
            
            # Log any errors that occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_names = [
                        "chat_restrictions",
                        "allowed_urls",
                        "external_daily",
                        "external_weekly",
                        "external_api_summary",
                        "external_daily_cost",
                        "external_weekly_cost",
                        "external_monthly_cost",
                        "top_costing_services",
                        "cost_summary"
                    ]
                    logger.error(f"❌ Error fetching {error_names[i]}: {str(result)}")
            
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ Consolidated admin dashboard data fetched in {duration:.2f}s")
            
            return {
                "chat_restrictions": chat_restrictions,
                "allowed_urls": allowed_urls,
                "external_daily": external_daily,
                "external_weekly": external_weekly,
                "external_api_summary": external_api_summary,
                "external_daily_cost": external_daily_cost,
                "external_weekly_cost": external_weekly_cost,
                "external_monthly_cost": external_monthly_cost,
                "top_costing_services": top_costing_services,
                "cost_summary": cost_summary,
                "server_info": self._get_server_info(),
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

    async def _get_external_api_summary(self, db: Session) -> List[Dict[str, Any]]:
        """Get external API usage summary (last 24 hours)"""
        try:
            analytics_service = AnalyticsService(db)
            summaries = analytics_service.summarize_external_usage(since_hours=24)
            return [s.model_dump() for s in summaries]
        except Exception as e:
            logger.error(f"Error fetching external API summary: {e}")
            return []

    async def _get_external_daily(self, db: Session) -> List[Dict[str, Any]]:
        try:
            analytics_service = AnalyticsService(db)
            return analytics_service.get_external_daily_usage(db, days=7)
        except Exception as e:
            logger.error(f"Error fetching external daily usage: {e}")
            return []

    async def _get_external_weekly(self, db: Session) -> List[Dict[str, Any]]:
        try:
            analytics_service = AnalyticsService(db)
            return analytics_service.get_external_weekly_usage(db, weeks=4)
        except Exception as e:
            logger.error(f"Error fetching external weekly usage: {e}")
            return []

    # Monthly external analytics intentionally removed per requirements
    
    async def _get_external_daily_cost(self, db: Session) -> List[Dict[str, Any]]:
        """Get daily cost analytics data (7 days)"""
        try:
            analytics_service = AnalyticsService(db)
            return analytics_service.get_external_daily_cost_usage(db, days=7)
        except Exception as e:
            logger.error(f"Error fetching external daily cost usage: {e}")
            return []

    async def _get_external_weekly_cost(self, db: Session) -> List[Dict[str, Any]]:
        """Get weekly cost analytics data (4 weeks)"""
        try:
            analytics_service = AnalyticsService(db)
            return analytics_service.get_external_weekly_cost_usage(db, weeks=4)
        except Exception as e:
            logger.error(f"Error fetching external weekly cost usage: {e}")
            return []

    async def _get_external_monthly_cost(self, db: Session) -> List[Dict[str, Any]]:
        """Get monthly cost analytics data (12 months)"""
        try:
            analytics_service = AnalyticsService(db)
            return analytics_service.get_external_monthly_cost_usage(db, months=12)
        except Exception as e:
            logger.error(f"Error fetching external monthly cost usage: {e}")
            return []

    async def _get_top_costing_services(self, db: Session) -> List[Dict[str, Any]]:
        """Get top costing services (last 30 days)"""
        try:
            analytics_service = AnalyticsService(db)
            return analytics_service.get_top_costing_services(db, limit=10, days=30)
        except Exception as e:
            logger.error(f"Error fetching top costing services: {e}")
            return []

    async def _get_cost_summary(self, db: Session) -> Dict[str, Any]:
        """Get comprehensive cost summary (last 30 days)"""
        try:
            analytics_service = AnalyticsService(db)
            return analytics_service.get_cost_summary(db, days=30)
        except Exception as e:
            logger.error(f"Error fetching cost summary: {e}")
            return {}

    async def get_cost_analytics_data(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive cost analytics data for admin dashboard
        
        Returns:
            Dict containing all cost analytics data:
            - daily_cost_trends: Daily cost trends (7 days)
            - weekly_cost_trends: Weekly cost trends (4 weeks)
            - monthly_cost_trends: Monthly cost trends (12 months)
            - top_costing_services: Top costing services
            - cost_summary: Overall cost summary
        """
        try:
            logger.info("🚀 Starting cost analytics data fetch")
            start_time = asyncio.get_event_loop().time()
            
            # Fetch all cost data concurrently for better performance
            results = await asyncio.gather(
                self._get_external_daily_cost(db),
                self._get_external_weekly_cost(db),
                self._get_external_monthly_cost(db),
                self._get_top_costing_services(db),
                self._get_cost_summary(db),
                return_exceptions=True
            )
            
            # Process results
            daily_cost_trends = results[0] if not isinstance(results[0], Exception) else []
            weekly_cost_trends = results[1] if not isinstance(results[1], Exception) else []
            monthly_cost_trends = results[2] if not isinstance(results[2], Exception) else []
            top_costing_services = results[3] if not isinstance(results[3], Exception) else []
            cost_summary = results[4] if not isinstance(results[4], Exception) else {}
            
            # Log any errors that occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_names = [
                        "daily_cost_trends",
                        "weekly_cost_trends", 
                        "monthly_cost_trends",
                        "top_costing_services",
                        "cost_summary"
                    ]
                    logger.error(f"❌ Error fetching {error_names[i]}: {str(result)}")
            
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ Cost analytics data fetched in {duration:.2f}s")
            
            return {
                "daily_cost_trends": daily_cost_trends,
                "weekly_cost_trends": weekly_cost_trends,
                "monthly_cost_trends": monthly_cost_trends,
                "top_costing_services": top_costing_services,
                "cost_summary": cost_summary,
                "metadata": {
                    "fetch_time": duration,
                    "timestamp": asyncio.get_event_loop().time(),
                    "period_days": days
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in get_cost_analytics_data: {str(e)}")
            raise e
    
    def _get_server_info(self) -> Dict[str, Any]:
        """Get server start time and uptime information"""
        try:
            from app.core.server_info import get_server_start_time, get_server_uptime
            
            start_time = get_server_start_time()
            uptime = get_server_uptime()
            
            return {
                "start_time": start_time.isoformat() if start_time else None,
                "uptime": uptime,
                "status": "running"
            }
        except Exception as e:
            logger.error(f"Error getting server info: {e}")
            return {
                "start_time": None,
                "uptime": None,
                "status": "unknown"
            }
