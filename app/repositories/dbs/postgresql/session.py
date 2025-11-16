"""PostgreSQL session management."""

from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

class PostgreSQLSessionManager:
    """Manages PostgreSQL database sessions."""
    
    def __init__(self):
        """Initialize session manager."""
        self._session: Optional[Session] = None
    
    def get_session(self) -> Session:
        """Get database session."""
        if not self._session:
            self._session = SessionLocal()
        return self._session
    
    def close_session(self):
        """Close database session."""
        if self._session:
            self._session.close()
            self._session = None

