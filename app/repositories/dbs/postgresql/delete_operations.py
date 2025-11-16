"""Delete operations for PostgreSQL repository."""

from typing import Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.helpers import logger, ExternalApiTimer

class PostgreSQLDeleteOperations:
    """Handles delete operations for PostgreSQL."""
    
    def __init__(self, session_manager, model_class: Optional[Type] = None, table_name: Optional[str] = None):
        """Initialize with session manager, optional model class, and table name."""
        self.session_manager = session_manager
        self.model_class = model_class
        self.table_name = table_name or 'entities'
    
    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        try:
            session = self.session_manager.get_session()
            
            if self.model_class:
                # Use SQLAlchemy model
                db_entity = session.query(self.model_class).filter(
                    self.model_class.id == entity_id
                ).first()
                
                if not db_entity:
                    return False
                
                session.delete(db_entity)
                session.commit()
                return True
            else:
                # Use raw SQL for generic operations
                query = f"DELETE FROM {self.table_name} WHERE id = :id"
                
                with ExternalApiTimer("postgresql", operation="delete") as t:
                    result = session.execute(text(query), {"id": entity_id})
                    session.commit()
                    t.set_status(status_code=200, success=(result.rowcount > 0))
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting entity: {str(e)}")
            session.rollback()
            return False

