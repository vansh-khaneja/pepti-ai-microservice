import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.analytics_service import AnalyticsService
from app.models.analytics import EndpointUsageCreate
from app.core.database import SessionLocal
from app.utils.helpers import logger

class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track endpoint usage"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        endpoint_path = request.url.path
        method = request.method
        user_agent = request.headers.get("user-agent")
        ip_address = self._get_client_ip(request)
        
        # Only track analytics for API endpoints
        if not endpoint_path.startswith("/api/"):
            return await call_next(request)
        
        db = None
        try:
            response = await call_next(request)
            response_time_ms = int((time.time() - start_time) * 1000)
            request_size_bytes = self._get_request_size(request)
            response_size_bytes = self._get_response_size(response)
            
            usage_data = EndpointUsageCreate(
                endpoint_path=endpoint_path,
                method=method,
                user_agent=user_agent,
                ip_address=ip_address,
                response_status=response.status_code,
                response_time_ms=response_time_ms,
                request_size_bytes=request_size_bytes,
                response_size_bytes=response_size_bytes,
                additional_data={
                    "query_params": dict(request.query_params),
                    "headers": dict(request.headers),
                    "path_params": getattr(request, "path_params", {})
                }
            )
            
            # Try to track analytics, but don't fail if it doesn't work
            try:
                db = SessionLocal()
                analytics_service = AnalyticsService(db)
                analytics_service.track_endpoint_usage(usage_data)
            except Exception as e:
                logger.warning(f"Failed to track analytics: {str(e)}")
                # Analytics failure shouldn't break the request
            
            return response
            
        except Exception as e:
            # Track error responses too
            response_time_ms = int((time.time() - start_time) * 1000)
            error_usage_data = EndpointUsageCreate(
                endpoint_path=endpoint_path,
                method=method,
                user_agent=user_agent,
                ip_address=ip_address,
                response_status=500,
                response_time_ms=response_time_ms,
                request_size_bytes=self._get_request_size(request),
                response_size_bytes=0,
                additional_data={
                    "error": str(e),
                    "query_params": dict(request.query_params),
                    "headers": dict(request.headers),
                    "path_params": getattr(request, "path_params", {})
                }
            )
            
            # Try to track error analytics, but don't fail if it doesn't work
            try:
                if db is None:
                    db = SessionLocal()
                analytics_service = AnalyticsService(db)
                analytics_service.track_endpoint_usage(error_usage_data)
            except Exception as tracking_error:
                logger.warning(f"Failed to track error analytics: {str(tracking_error)}")
            
            raise
        finally:
            if db:
                try:
                    db.close()
                except:
                    pass
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"
    
    def _get_request_size(self, request: Request) -> int:
        """Estimate request size in bytes"""
        try:
            # Basic size estimation
            size = len(str(request.url))
            size += sum(len(f"{k}: {v}") for k, v in request.headers.items())
            
            # Add body size if available
            if hasattr(request, '_body'):
                size += len(request._body)
            
            return size
        except:
            return 0
    
    def _get_response_size(self, response: Response) -> int:
        """Get response size in bytes"""
        try:
            if hasattr(response, 'body'):
                return len(response.body)
            return 0
        except:
            return 0
