from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.models.analytics import (
    EndpointUsage, EndpointUsageCreate,
    ExternalApiUsage, ExternalApiUsageCreate, ExternalApiUsageSummary
)
from app.utils.helpers import logger
from app.repositories import repository_manager
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
import json
import statistics

class AnalyticsService:
    def __init__(self, db: Session = None):
        # Keep db for backward compatibility but use repository pattern
        self.db = db
        self.relational_repo = repository_manager.relational
    
    def track_endpoint_usage(self, usage_data: EndpointUsageCreate) -> Dict[str, Any]:
        """Track endpoint usage using relational repository"""
        try:
            entity = usage_data.model_dump()
            entity["table_name"] = "endpoint_usage"  # Specify table name
            result = self.relational_repo.create(entity)
            logger.info(f"Tracked endpoint usage: {usage_data.endpoint_path} {usage_data.method}")
            return result
        except Exception as e:
            logger.error(f"Error tracking endpoint usage: {str(e)}")
            raise

    def track_external_api_usage(self, usage: ExternalApiUsageCreate) -> Dict[str, Any]:
        """Track an external API call usage using relational repository"""
        try:
            entity = {
                "provider": usage.provider.lower(),
                "operation": usage.operation,
                "status_code": usage.status_code,
                "success": 1 if usage.success else 0,
                "latency_ms": usage.latency_ms,
                "request_bytes": usage.request_bytes,
                "response_bytes": usage.response_bytes,
                "metadata": json.dumps(usage.metadata) if usage.metadata else None,  # Use correct column name
                # Cost tracking fields
                "cost_usd": usage.cost_usd,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "pricing_model": usage.pricing_model,
                "table_name": "external_api_usage"  # Specify table name
            }
            result = self.relational_repo.create(entity)
            logger.info(f"Tracked external API usage: {usage.provider} {usage.operation or ''}")
            return result
        except Exception as e:
            logger.error(f"Error tracking external API usage: {str(e)}")
            raise

    def summarize_external_usage(self, since_hours: int = 24) -> list[ExternalApiUsageSummary]:
        """Return summary stats by provider for recent period"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=since_hours)
            q = (
                self.db.query(
                    ExternalApiUsage.provider,
                    func.count(ExternalApiUsage.id),
                    func.sum(ExternalApiUsage.success),
                    func.sum(1 - ExternalApiUsage.success),
                    func.avg(ExternalApiUsage.latency_ms),
                    func.sum(ExternalApiUsage.cost_usd),
                    func.sum(ExternalApiUsage.input_tokens),
                    func.sum(ExternalApiUsage.output_tokens)
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by(ExternalApiUsage.provider)
            )
            rows = q.all()
            by_provider: dict[str, ExternalApiUsageSummary] = {}
            for provider, total, succ, fail, avg_lat, total_cost, total_input_tokens, total_output_tokens in rows:
                total_calls = int(total or 0)
                avg_cost_per_call = float(total_cost or 0) / total_calls if total_calls > 0 else 0.0
                
                by_provider[provider.lower()] = ExternalApiUsageSummary(
                    provider=provider.lower(),
                    total_calls=total_calls,
                    successes=int(succ or 0),
                    failures=int(fail or 0),
                    avg_latency_ms=float(avg_lat) if avg_lat is not None else 0.0,
                    # Cost tracking fields
                    total_cost_usd=float(total_cost or 0),
                    avg_cost_per_call=avg_cost_per_call,
                    total_input_tokens=int(total_input_tokens or 0),
                    total_output_tokens=int(total_output_tokens or 0)
                )

            # Ensure all providers are present, even if zero
            expected = ["qdrant", "openai", "serpapi", "tavily"]
            for p in expected:
                if p not in by_provider:
                    by_provider[p] = ExternalApiUsageSummary(
                        provider=p,
                        total_calls=0,
                        successes=0,
                        failures=0,
                        avg_latency_ms=0.0,
                        # Cost tracking fields
                        total_cost_usd=0.0,
                        avg_cost_per_call=0.0,
                        total_input_tokens=0,
                        total_output_tokens=0
                    )
            # Return in a stable order
            return [by_provider[p] for p in expected]
        except Exception as e:
            logger.error(f"Error summarizing external API usage: {str(e)}")
            raise

    def get_external_daily_usage(self, db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Daily external API hits for the last N days, per provider, zero-filled."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days - 1)
            # Truncate to day and count per provider
            rows = (
                db.query(
                    func.date_trunc('day', ExternalApiUsage.created_at).label('d'),
                    ExternalApiUsage.provider,
                    func.count(ExternalApiUsage.id).label('hits')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by('d', ExternalApiUsage.provider)
                .order_by('d')
                .all()
            )

            # Build day list
            today = datetime.utcnow().date()
            days_list = [today - timedelta(days=i) for i in range(days)][::-1]
            expected = ["qdrant", "openai", "serpapi", "tavily"]

            # Map rows
            by_day: Dict[date, Dict[str, int]] = {}
            for d, provider, hits in rows:
                day_key = d.date()
                if day_key not in by_day:
                    by_day[day_key] = {}
                by_day[day_key][provider.lower()] = int(hits)

            # Zero-fill and format
            output: List[Dict[str, Any]] = []
            for d in days_list:
                providers = []
                for p in expected:
                    providers.append({
                        "provider": p,
                        "hits": by_day.get(d, {}).get(p, 0)
                    })
                output.append({
                    "date": d.isoformat(),
                    "providers": providers
                })
            return output
        except Exception as e:
            logger.error(f"Error getting external daily usage: {str(e)}")
            return []

    def get_external_weekly_usage(self, db: Session, weeks: int = 4) -> List[Dict[str, Any]]:
        """Weekly external API hits for last N ISO weeks, per provider, zero-filled."""
        try:
            cutoff = datetime.utcnow() - timedelta(weeks=weeks - 1)
            rows = (
                db.query(
                    func.date_trunc('week', ExternalApiUsage.created_at).label('w'),
                    ExternalApiUsage.provider,
                    func.count(ExternalApiUsage.id).label('hits')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by('w', ExternalApiUsage.provider)
                .order_by('w')
                .all()
            )

            # Build week list (start Mondays from date_trunc)
            expected = ["qdrant", "openai", "serpapi", "tavily"]
            by_week: Dict[str, Dict[str, int]] = {}
            for w, provider, hits in rows:
                # Label as ISO week string, e.g., 2025-W39
                wk = w.date().isocalendar()
                label = f"{wk.year}-W{wk.week:02d}"
                if label not in by_week:
                    by_week[label] = {}
                by_week[label][provider.lower()] = int(hits)

            # Generate last N week labels
            labels: List[str] = []
            cur = datetime.utcnow().date()
            for _ in range(weeks):
                iso = cur.isocalendar()
                labels.append(f"{iso.year}-W{iso.week:02d}")
                cur -= timedelta(days=7)
            labels = labels[::-1]

            output: List[Dict[str, Any]] = []
            for lab in labels:
                providers = []
                for p in expected:
                    providers.append({
                        "provider": p,
                        "hits": by_week.get(lab, {}).get(p, 0)
                    })
                output.append({
                    "week": lab,
                    "providers": providers
                })
            return output
        except Exception as e:
            logger.error(f"Error getting external weekly usage: {str(e)}")
            return []

    def get_external_monthly_usage(self, db: Session, months: int = 12) -> List[Dict[str, Any]]:
        """Monthly external API hits for last N months, per provider, zero-filled."""
        try:
            # Approx cutoff: months back; simpler approach using 365/12
            cutoff = datetime.utcnow() - timedelta(days=int(months * 30.4))
            rows = (
                db.query(
                    func.date_trunc('month', ExternalApiUsage.created_at).label('m'),
                    ExternalApiUsage.provider,
                    func.count(ExternalApiUsage.id).label('hits')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by('m', ExternalApiUsage.provider)
                .order_by('m')
                .all()
            )

            expected = ["qdrant", "openai", "serpapi", "tavily"]
            by_month: Dict[str, Dict[str, int]] = {}
            for m, provider, hits in rows:
                label = m.strftime("%Y-%m")
                if label not in by_month:
                    by_month[label] = {}
                by_month[label][provider.lower()] = int(hits)

            # Generate last N month labels
            labels: List[str] = []
            today = datetime.utcnow()
            y = today.year
            mo = today.month
            for _ in range(months):
                labels.append(f"{y:04d}-{mo:02d}")
                mo -= 1
                if mo == 0:
                    mo = 12
                    y -= 1
            labels = labels[::-1]

            output: List[Dict[str, Any]] = []
            for lab in labels:
                providers = []
                for p in expected:
                    providers.append({
                        "provider": p,
                        "hits": by_month.get(lab, {}).get(p, 0)
                    })
                output.append({
                    "month": lab,
                    "providers": providers
                })
            return output
        except Exception as e:
            logger.error(f"Error getting external monthly usage: {str(e)}")
            return []
    
    def get_daily_endpoint_usage(self, db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Get endpoint usage per day for last N days"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            daily_usage = db.query(
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
    
    def get_weekly_endpoint_usage(self, db: Session, weeks: int = 1) -> List[Dict[str, Any]]:
        """Get endpoint usage per week for last N weeks"""
        try:
            start_date = datetime.now() - timedelta(weeks=weeks)
            
            weekly_usage = db.query(
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
    
    def get_monthly_endpoint_usage(self, db: Session, months: int = 12) -> List[Dict[str, Any]]:
        """Get overall endpoint usage per month for last N months"""
        try:
            start_date = datetime.now() - timedelta(days=months*30)
            
            monthly_usage = db.query(
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

    def get_external_daily_cost_usage(self, db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """Daily external API costs for the last N days, per provider, zero-filled."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days - 1)
            # Truncate to day and sum costs per provider
            rows = (
                db.query(
                    func.date_trunc('day', ExternalApiUsage.created_at).label('d'),
                    ExternalApiUsage.provider,
                    func.count(ExternalApiUsage.id).label('calls'),
                    func.sum(ExternalApiUsage.cost_usd).label('total_cost'),
                    func.avg(ExternalApiUsage.cost_usd).label('avg_cost_per_call')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by('d', ExternalApiUsage.provider)
                .order_by('d')
                .all()
            )

            # Build day list
            today = datetime.utcnow().date()
            days_list = [today - timedelta(days=i) for i in range(days)][::-1]
            expected = ["qdrant", "openai", "serpapi", "tavily"]

            # Map rows
            by_day: Dict[date, Dict[str, Dict[str, Any]]] = {}
            for d, provider, calls, total_cost, avg_cost in rows:
                day_key = d.date()
                if day_key not in by_day:
                    by_day[day_key] = {}
                by_day[day_key][provider.lower()] = {
                    "calls": int(calls or 0),
                    "total_cost": float(total_cost or 0),
                    "avg_cost_per_call": float(avg_cost or 0)
                }

            # Zero-fill and format
            output: List[Dict[str, Any]] = []
            for d in days_list:
                providers = []
                for p in expected:
                    provider_data = by_day.get(d, {}).get(p, {
                        "calls": 0,
                        "total_cost": 0.0,
                        "avg_cost_per_call": 0.0
                    })
                    providers.append({
                        "provider": p,
                        "calls": provider_data["calls"],
                        "total_cost": provider_data["total_cost"],
                        "avg_cost_per_call": provider_data["avg_cost_per_call"]
                    })
                output.append({
                    "date": d.isoformat(),
                    "providers": providers
                })
            return output
        except Exception as e:
            logger.error(f"Error getting external daily cost usage: {str(e)}")
            return []

    def get_external_weekly_cost_usage(self, db: Session, weeks: int = 4) -> List[Dict[str, Any]]:
        """Weekly external API costs for last N ISO weeks, per provider, zero-filled."""
        try:
            cutoff = datetime.utcnow() - timedelta(weeks=weeks - 1)
            rows = (
                db.query(
                    func.date_trunc('week', ExternalApiUsage.created_at).label('w'),
                    ExternalApiUsage.provider,
                    func.count(ExternalApiUsage.id).label('calls'),
                    func.sum(ExternalApiUsage.cost_usd).label('total_cost'),
                    func.avg(ExternalApiUsage.cost_usd).label('avg_cost_per_call')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by('w', ExternalApiUsage.provider)
                .order_by('w')
                .all()
            )

            # Build week list (start Mondays from date_trunc)
            expected = ["qdrant", "openai", "serpapi", "tavily"]
            by_week: Dict[str, Dict[str, Dict[str, Any]]] = {}
            for w, provider, calls, total_cost, avg_cost in rows:
                # Label as ISO week string, e.g., 2025-W39
                wk = w.date().isocalendar()
                label = f"{wk.year}-W{wk.week:02d}"
                if label not in by_week:
                    by_week[label] = {}
                by_week[label][provider.lower()] = {
                    "calls": int(calls or 0),
                    "total_cost": float(total_cost or 0),
                    "avg_cost_per_call": float(avg_cost or 0)
                }

            # Generate last N week labels
            labels: List[str] = []
            cur = datetime.utcnow().date()
            for _ in range(weeks):
                iso = cur.isocalendar()
                labels.append(f"{iso.year}-W{iso.week:02d}")
                cur -= timedelta(days=7)
            labels = labels[::-1]

            output: List[Dict[str, Any]] = []
            for lab in labels:
                providers = []
                for p in expected:
                    provider_data = by_week.get(lab, {}).get(p, {
                        "calls": 0,
                        "total_cost": 0.0,
                        "avg_cost_per_call": 0.0
                    })
                    providers.append({
                        "provider": p,
                        "calls": provider_data["calls"],
                        "total_cost": provider_data["total_cost"],
                        "avg_cost_per_call": provider_data["avg_cost_per_call"]
                    })
                output.append({
                    "week": lab,
                    "providers": providers
                })
            return output
        except Exception as e:
            logger.error(f"Error getting external weekly cost usage: {str(e)}")
            return []

    def get_external_monthly_cost_usage(self, db: Session, months: int = 12) -> List[Dict[str, Any]]:
        """Monthly external API costs for last N months, per provider, zero-filled."""
        try:
            # Approx cutoff: months back; simpler approach using 365/12
            cutoff = datetime.utcnow() - timedelta(days=int(months * 30.4))
            rows = (
                db.query(
                    func.date_trunc('month', ExternalApiUsage.created_at).label('m'),
                    ExternalApiUsage.provider,
                    func.count(ExternalApiUsage.id).label('calls'),
                    func.sum(ExternalApiUsage.cost_usd).label('total_cost'),
                    func.avg(ExternalApiUsage.cost_usd).label('avg_cost_per_call')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by('m', ExternalApiUsage.provider)
                .order_by('m')
                .all()
            )

            expected = ["qdrant", "openai", "serpapi", "tavily"]
            by_month: Dict[str, Dict[str, Dict[str, Any]]] = {}
            for m, provider, calls, total_cost, avg_cost in rows:
                label = m.strftime("%Y-%m")
                if label not in by_month:
                    by_month[label] = {}
                by_month[label][provider.lower()] = {
                    "calls": int(calls or 0),
                    "total_cost": float(total_cost or 0),
                    "avg_cost_per_call": float(avg_cost or 0)
                }

            # Generate last N month labels
            labels: List[str] = []
            today = datetime.utcnow()
            y = today.year
            mo = today.month
            for _ in range(months):
                labels.append(f"{y:04d}-{mo:02d}")
                mo -= 1
                if mo == 0:
                    mo = 12
                    y -= 1
            labels = labels[::-1]

            output: List[Dict[str, Any]] = []
            for lab in labels:
                providers = []
                for p in expected:
                    provider_data = by_month.get(lab, {}).get(p, {
                        "calls": 0,
                        "total_cost": 0.0,
                        "avg_cost_per_call": 0.0
                    })
                    providers.append({
                        "provider": p,
                        "calls": provider_data["calls"],
                        "total_cost": provider_data["total_cost"],
                        "avg_cost_per_call": provider_data["avg_cost_per_call"]
                    })
                output.append({
                    "month": lab,
                    "providers": providers
                })
            return output
        except Exception as e:
            logger.error(f"Error getting external monthly cost usage: {str(e)}")
            return []

    def get_top_costing_services(self, db: Session, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """Get top costing services by total cost over the last N days"""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Get top services by total cost
            top_services = (
                db.query(
                    ExternalApiUsage.provider,
                    ExternalApiUsage.operation,
                    func.count(ExternalApiUsage.id).label('total_calls'),
                    func.sum(ExternalApiUsage.cost_usd).label('total_cost'),
                    func.avg(ExternalApiUsage.cost_usd).label('avg_cost_per_call'),
                    func.sum(ExternalApiUsage.input_tokens).label('total_input_tokens'),
                    func.sum(ExternalApiUsage.output_tokens).label('total_output_tokens')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by(ExternalApiUsage.provider, ExternalApiUsage.operation)
                .order_by(desc('total_cost'))
                .limit(limit)
                .all()
            )
            
            result = []
            for provider, operation, calls, total_cost, avg_cost, input_tokens, output_tokens in top_services:
                result.append({
                    "provider": provider,
                    "operation": operation or "unknown",
                    "total_calls": int(calls or 0),
                    "total_cost": float(total_cost or 0),
                    "avg_cost_per_call": float(avg_cost or 0),
                    "total_input_tokens": int(input_tokens or 0),
                    "total_output_tokens": int(output_tokens or 0),
                    "cost_percentage": 0.0  # Will be calculated after getting total
                })
            
            # Calculate cost percentages
            if result:
                total_cost = sum(item["total_cost"] for item in result)
                if total_cost > 0:
                    for item in result:
                        item["cost_percentage"] = (item["total_cost"] / total_cost) * 100
            
            return result
        except Exception as e:
            logger.error(f"Error getting top costing services: {str(e)}")
            return []

    def get_cost_summary(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive cost summary for the last N days"""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Get overall cost statistics
            overall_stats = (
                db.query(
                    func.count(ExternalApiUsage.id).label('total_calls'),
                    func.sum(ExternalApiUsage.cost_usd).label('total_cost'),
                    func.avg(ExternalApiUsage.cost_usd).label('avg_cost_per_call'),
                    func.min(ExternalApiUsage.cost_usd).label('min_cost'),
                    func.max(ExternalApiUsage.cost_usd).label('max_cost'),
                    func.sum(ExternalApiUsage.input_tokens).label('total_input_tokens'),
                    func.sum(ExternalApiUsage.output_tokens).label('total_output_tokens')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .first()
            )
            
            # Get cost by provider
            provider_stats = (
                db.query(
                    ExternalApiUsage.provider,
                    func.count(ExternalApiUsage.id).label('calls'),
                    func.sum(ExternalApiUsage.cost_usd).label('total_cost'),
                    func.avg(ExternalApiUsage.cost_usd).label('avg_cost_per_call')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by(ExternalApiUsage.provider)
                .order_by(desc('total_cost'))
                .all()
            )
            
            # Get daily cost trend
            daily_trend = (
                db.query(
                    func.date_trunc('day', ExternalApiUsage.created_at).label('date'),
                    func.sum(ExternalApiUsage.cost_usd).label('daily_cost')
                )
                .filter(ExternalApiUsage.created_at >= cutoff)
                .group_by(func.date_trunc('day', ExternalApiUsage.created_at))
                .order_by('date')
                .all()
            )
            
            return {
                "period_days": days,
                "overall": {
                    "total_calls": int(overall_stats.total_calls or 0),
                    "total_cost": float(overall_stats.total_cost or 0),
                    "avg_cost_per_call": float(overall_stats.avg_cost_per_call or 0),
                    "min_cost": float(overall_stats.min_cost or 0),
                    "max_cost": float(overall_stats.max_cost or 0),
                    "total_input_tokens": int(overall_stats.total_input_tokens or 0),
                    "total_output_tokens": int(overall_stats.total_output_tokens or 0)
                },
                "by_provider": [
                    {
                        "provider": provider,
                        "calls": int(calls or 0),
                        "total_cost": float(total_cost or 0),
                        "avg_cost_per_call": float(avg_cost or 0),
                        "cost_percentage": 0.0  # Will be calculated
                    }
                    for provider, calls, total_cost, avg_cost in provider_stats
                ],
                "daily_trend": [
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "cost": float(daily_cost or 0)
                    }
                    for date, daily_cost in daily_trend
                ]
            }
        except Exception as e:
            logger.error(f"Error getting cost summary: {str(e)}")
            return {
                "period_days": days,
                "overall": {
                    "total_calls": 0,
                    "total_cost": 0.0,
                    "avg_cost_per_call": 0.0,
                    "min_cost": 0.0,
                    "max_cost": 0.0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0
                },
                "by_provider": [],
                "daily_trend": []
            }