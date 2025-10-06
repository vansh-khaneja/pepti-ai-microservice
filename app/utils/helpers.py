import logging
from typing import Any, Dict, List, Optional
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def format_response(data: Any = None, message: str = "Success", success: bool = True) -> Dict[str, Any]:
    """Format API response consistently"""
    return {
        "success": success,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }

def log_api_call(endpoint: str, method: str, user_agent: str = None, **kwargs):
    """Log API calls for monitoring"""
    logger.info(f"API Call: {method} {endpoint} - User-Agent: {user_agent}")


class ExternalApiTimer:
    """Context manager to time external API calls and record analytics"""
    def __init__(self, provider: str, operation: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.provider = provider
        self.operation = operation
        self.metadata = metadata or {}
        self.start_ns = 0
        self.response_bytes = None
        self.request_bytes = None
        self.status_code = None
        self.success = True

    def __enter__(self):
        self.start_ns = time.perf_counter_ns()
        return self

    def set_io(self, request_bytes: Optional[int], response_bytes: Optional[int]):
        self.request_bytes = request_bytes
        self.response_bytes = response_bytes

    def set_status(self, status_code: Optional[int], success: bool):
        self.status_code = status_code
        self.success = success

    def __exit__(self, exc_type, exc, tb):
        latency_ms = int((time.perf_counter_ns() - self.start_ns) / 1_000_000)
        db = None
        try:
            # Lazy imports to avoid circular import on module load
            from app.core.database import SessionLocal  # local import
            from app.services.analytics_service import AnalyticsService  # local import
            from app.models.analytics import ExternalApiUsageCreate  # local import

            db = SessionLocal()
            svc = AnalyticsService(db)
            svc.track_external_api_usage(ExternalApiUsageCreate(
                provider=self.provider,
                operation=self.operation,
                status_code=self.status_code,
                success=self.success and exc is None,
                latency_ms=latency_ms,
                request_bytes=self.request_bytes,
                response_bytes=self.response_bytes,
                metadata=self.metadata
            ))
        except Exception as e:
            logger.warning(f"Failed to record external API usage: {e}")
        finally:
            if db:
                db.close()

def validate_search_query(query: str) -> bool:
    """Validate search query parameters"""
    if not query or not query.strip():
        return False
    if len(query.strip()) < 2:
        return False
    return True
