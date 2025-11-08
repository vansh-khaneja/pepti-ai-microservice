import logging
from typing import Any, Dict, List, Optional
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Thread pool executor for background database operations
_db_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="analytics_db")

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
            
            # Log immediately (non-blocking)
            logger.debug(f"External API call: {self.provider} {self.operation} - {latency_ms}ms - {'success' if success else 'failed'}")
            
            # Calculate cost and save to database in background (non-blocking)
            # This ensures response is sent before cost calculation and DB save
            # Pass metadata reference - copy will happen in background thread to avoid blocking
            _calculate_and_save_analytics_background(
                provider=self.provider,
                operation=self.operation,
                status_code=self.status_code,
                success=success,
                latency_ms=latency_ms,
                request_bytes=self.request_bytes,
                response_bytes=self.response_bytes,
                metadata=self.metadata,  # Pass reference, copy in background
                # Cost data - will be calculated in background if not set
                cost_usd=self.cost_usd,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                pricing_model=self.pricing_model,
                needs_cost_calculation=(self.cost_usd == 0.0 and self.pricing_model is None)
            )
        else:
            # Skip tracking for internal services like PostgreSQL
            logger.debug(f"Internal service call: {self.provider} {self.operation} - {latency_ms}ms - {'success' if self.success and exc is None else 'failed'}")


def _calculate_and_save_analytics_background(
    provider: str,
    operation: Optional[str],
    status_code: Optional[int],
    success: bool,
    latency_ms: int,
    request_bytes: Optional[int],
    response_bytes: Optional[int],
    metadata: Dict[str, Any],
    cost_usd: float,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    pricing_model: Optional[str],
    needs_cost_calculation: bool
):
    """Background function to calculate cost and save analytics to database (non-blocking)"""
    def _calculate_and_save():
        try:
            # Copy metadata in background thread to avoid blocking (metadata may contain large text)
            metadata_copy = metadata.copy() if metadata else {}
            
            # Calculate cost in background if needed
            final_cost_usd = cost_usd
            final_input_tokens = input_tokens
            final_output_tokens = output_tokens
            final_pricing_model = pricing_model
            
            if needs_cost_calculation:
                try:
                    from app.services.cost_calculator import cost_calculator
                    
                    calculated_cost, calc_pricing_model, calc_input_tokens, calc_output_tokens = cost_calculator.calculate_cost(
                        provider=provider,
                        operation=operation,
                        metadata=metadata_copy
                    )
                    
                    final_cost_usd = calculated_cost
                    final_pricing_model = calc_pricing_model or final_pricing_model
                    # Only use calculated tokens if we don't already have actual tokens from API
                    if final_input_tokens is None:
                        final_input_tokens = calc_input_tokens
                    if final_output_tokens is None:
                        final_output_tokens = calc_output_tokens
                    
                    logger.debug(f"Calculated cost in background for {provider} {operation}: ${final_cost_usd:.6f}")
                except Exception as e:
                    logger.error(f"Error calculating cost in background for {provider}: {e}")
                    # Continue with default values
            
            from app.services.analytics_service import AnalyticsService
            from app.models.analytics import ExternalApiUsageCreate
            from app.core.database import SessionLocal
            
            # Create usage record with cost data
            usage_data = ExternalApiUsageCreate(
                provider=provider,
                operation=operation,
                status_code=status_code,
                success=success,
                latency_ms=latency_ms,
                request_bytes=request_bytes,
                response_bytes=response_bytes,
                metadata=metadata_copy,
                # Cost tracking fields
                cost_usd=final_cost_usd,
                input_tokens=final_input_tokens,
                output_tokens=final_output_tokens,
                pricing_model=final_pricing_model
            )
            
            # Use the existing analytics service
            db = SessionLocal()
            try:
                analytics_service = AnalyticsService(db)
                analytics_service.track_external_api_usage(usage_data)
                logger.info(f"✅ External API usage saved to database: {provider} {operation} - {latency_ms}ms - ${final_cost_usd:.6f}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate cost and save external API usage to database: {e}")
            # Continue silently - analytics failures shouldn't affect main flow
    
    # Submit to thread pool executor (non-blocking)
    _db_executor.submit(_calculate_and_save)

def validate_search_query(query: str) -> bool:
    """Validate search query parameters"""
    if not query or not query.strip():
        return False
    if len(query.strip()) < 2:
        return False
    return True
