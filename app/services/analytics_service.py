from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.models.analytics import EndpointUsage, EndpointUsageCreate
from app.utils.helpers import logger
from typing import List, Dict, Any
from datetime import datetime, timedelta

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
    
    def track_endpoint_usage(self, usage_data: EndpointUsageCreate) -> EndpointUsage:
        """Track endpoint usage"""
        try:
            db_usage = EndpointUsage(**usage_data.model_dump())
            self.db.add(db_usage)
            self.db.commit()
            self.db.refresh(db_usage)
            logger.info(f"Tracked endpoint usage: {usage_data.endpoint_path} {usage_data.method}")
            return db_usage
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error tracking endpoint usage: {str(e)}")
            raise
    
    def get_daily_endpoint_usage(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get endpoint usage per day for last N days"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            daily_usage = self.db.query(
                func.date(EndpointUsage.created_at).label('date'),
                EndpointUsage.endpoint_path,
                EndpointUsage.method,
                func.count(EndpointUsage.id).label('hit_count')
            ).filter(
                EndpointUsage.created_at >= start_date
            ).group_by(
                func.date(EndpointUsage.created_at),
                EndpointUsage.endpoint_path,
                EndpointUsage.method
            ).order_by(
                func.date(EndpointUsage.created_at),
                desc('hit_count')
            ).all()
            
            # Group by date
            result = {}
            for row in daily_usage:
                date_str = row.date.strftime("%Y-%m-%d")
                if date_str not in result:
                    result[date_str] = []
                
                result[date_str].append({
                    "endpoint": f"{row.method} {row.endpoint_path}",
                    "hits": row.hit_count
                })
            
            # Convert to list format
            return [
                {
                    "date": date,
                    "endpoints": endpoints
                }
                for date, endpoints in result.items()
            ]
            
        except Exception as e:
            logger.error(f"Error getting daily endpoint usage: {str(e)}")
            raise
    
    def get_weekly_endpoint_usage(self, weeks: int = 1) -> List[Dict[str, Any]]:
        """Get endpoint usage per week for last N weeks"""
        try:
            start_date = datetime.now() - timedelta(weeks=weeks)
            
            weekly_usage = self.db.query(
                func.date_trunc('week', EndpointUsage.created_at).label('week'),
                EndpointUsage.endpoint_path,
                EndpointUsage.method,
                func.count(EndpointUsage.id).label('hit_count')
            ).filter(
                EndpointUsage.created_at >= start_date
            ).group_by(
                func.date_trunc('week', EndpointUsage.created_at),
                EndpointUsage.endpoint_path,
                EndpointUsage.method
            ).order_by(
                func.date_trunc('week', EndpointUsage.created_at),
                desc('hit_count')
            ).all()
            
            # Group by week
            result = {}
            for row in weekly_usage:
                week_str = row.week.strftime("%Y-W%U")
                if week_str not in result:
                    result[week_str] = []
                
                result[week_str].append({
                    "endpoint": f"{row.method} {row.endpoint_path}",
                    "hits": row.hit_count
                })
            
            # Convert to list format
            return [
                {
                    "week": week,
                    "endpoints": endpoints
                }
                for week, endpoints in result.items()
            ]
            
        except Exception as e:
            logger.error(f"Error getting weekly endpoint usage: {str(e)}")
            raise
    
    def get_monthly_overall_usage(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get overall endpoint usage per month for last N months"""
        try:
            start_date = datetime.now() - timedelta(days=months*30)
            
            monthly_usage = self.db.query(
                func.date_trunc('month', EndpointUsage.created_at).label('month'),
                func.count(EndpointUsage.id).label('total_hits'),
                func.count(func.distinct(EndpointUsage.endpoint_path)).label('unique_endpoints')
            ).filter(
                EndpointUsage.created_at >= start_date
            ).group_by(
                func.date_trunc('month', EndpointUsage.created_at)
            ).order_by(
                func.date_trunc('month', EndpointUsage.created_at)
            ).all()
            
            return [
                {
                    "month": row.month.strftime("%Y-%m"),
                    "total_hits": row.total_hits,
                    "unique_endpoints": row.unique_endpoints
                }
                for row in monthly_usage
            ]
            
        except Exception as e:
            logger.error(f"Error getting monthly overall usage: {str(e)}")
            raise
    

