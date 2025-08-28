import logging
from typing import Any, Dict, List
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

def validate_search_query(query: str) -> bool:
    """Validate search query parameters"""
    if not query or not query.strip():
        return False
    if len(query.strip()) < 2:
        return False
    return True
