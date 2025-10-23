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
        # Cost tracking fields
        self.cost_usd = 0.0
        self.input_tokens = None
        self.output_tokens = None
        self.pricing_model = None

    def __enter__(self):
        self.start_ns = time.perf_counter_ns()
        return self

    def set_io(self, request_bytes: Optional[int], response_bytes: Optional[int]):
        self.request_bytes = request_bytes
        self.response_bytes = response_bytes

    def set_status(self, status_code: Optional[int], success: bool):
        self.status_code = status_code
        self.success = success

    def set_cost_data(self, cost_usd: float, input_tokens: Optional[int] = None, output_tokens: Optional[int] = None, pricing_model: Optional[str] = None):
        """Set cost data for the API call"""
        self.cost_usd = cost_usd
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.pricing_model = pricing_model

    def calculate_cost(self) -> None:
        """Calculate cost based on provider and metadata"""
        try:
            from app.services.cost_calculator import cost_calculator
            
            cost, pricing_model, input_tokens, output_tokens = cost_calculator.calculate_cost(
                provider=self.provider,
                operation=self.operation,
                metadata=self.metadata
            )
            
            self.cost_usd = cost
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens
            self.pricing_model = pricing_model
            
            logger.debug(f"Calculated cost for {self.provider} {self.operation}: ${cost:.6f}")
            
        except Exception as e:
            logger.error(f"Error calculating cost for {self.provider}: {e}")
            self.cost_usd = 0.0
            self.pricing_model = f"{self.provider}-{self.operation}"

    def __exit__(self, exc_type, exc, tb):
        latency_ms = int((time.perf_counter_ns() - self.start_ns) / 1_000_000)
        
        # Only track external services (not our own PostgreSQL database)
        external_providers = {'openai', 'qdrant', 'tavily', 'serpapi'}
        
        if self.provider.lower() in external_providers:
            success = self.success and exc is None
            
            # Calculate cost if not already set
            if self.cost_usd == 0.0 and self.pricing_model is None:
                self.calculate_cost()
            
            logger.debug(f"External API call: {self.provider} {self.operation} - {latency_ms}ms - ${self.cost_usd:.6f} - {'success' if success else 'failed'}")
            
            # Use existing analytics service (proven to work)
            try:
                from app.services.analytics_service import AnalyticsService
                from app.models.analytics import ExternalApiUsageCreate
                from app.core.database import SessionLocal
                
                # Create usage record with cost data
                usage_data = ExternalApiUsageCreate(
                    provider=self.provider,
                    operation=self.operation,
                    status_code=self.status_code,
                    success=success,
                    latency_ms=latency_ms,
                    request_bytes=self.request_bytes,
                    response_bytes=self.response_bytes,
                    metadata=self.metadata,
                    # Cost tracking fields
                    cost_usd=self.cost_usd,
                    input_tokens=self.input_tokens,
                    output_tokens=self.output_tokens,
                    pricing_model=self.pricing_model
                )
                
                # Use the existing analytics service
                db = SessionLocal()
                try:
                    analytics_service = AnalyticsService(db)
                    analytics_service.track_external_api_usage(usage_data)
                    logger.info(f"✅ External API usage saved to database: {self.provider} {self.operation} - {latency_ms}ms - ${self.cost_usd:.6f}")
                finally:
                    db.close()
                
            except Exception as e:
                logger.error(f"❌ Failed to save external API usage to database: {e}")
                # Continue with console logging as fallback
        else:
            # Skip tracking for internal services like PostgreSQL
            logger.debug(f"Internal service call: {self.provider} {self.operation} - {latency_ms}ms - {'success' if self.success and exc is None else 'failed'}")

def validate_search_query(query: str) -> bool:
    """Validate search query parameters"""
    if not query or not query.strip():
        return False
    if len(query.strip()) < 2:
        return False
    return True
