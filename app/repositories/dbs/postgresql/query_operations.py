"""Query operations for PostgreSQL repository."""

from typing import Dict, Any, List, Optional
from sqlalchemy import text
from app.utils.helpers import logger, ExternalApiTimer

class PostgreSQLQueryOperations:
    """Handles query operations for PostgreSQL."""
    
    def __init__(self, session_manager):
        """Initialize with session manager."""
        self.session_manager = session_manager
    
    def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query."""
        try:
            session = self.session_manager.get_session()
            
            with ExternalApiTimer("postgresql", operation="raw_query") as t:
                result = session.execute(text(query), params or {})
                rows = result.fetchall()
                t.set_status(status_code=200, success=True)
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Error executing raw query: {str(e)}")
            return []

