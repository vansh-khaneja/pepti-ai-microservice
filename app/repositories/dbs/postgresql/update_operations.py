"""Update operations for PostgreSQL repository."""

from typing import Dict, Any, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.helpers import logger, ExternalApiTimer

class PostgreSQLUpdateOperations:
    """Handles update operations for PostgreSQL."""
    
    def __init__(self, session_manager, model_class: Optional[Type] = None, table_name: Optional[str] = None):
        """Initialize with session manager, optional model class, and table name."""
        self.session_manager = session_manager
        self.model_class = model_class
        self.table_name = table_name or 'entities'
    
    def update(self, entity_id: str, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an entity."""
        try:
            session = self.session_manager.get_session()
            
            if self.model_class:
                # Use SQLAlchemy model
                db_entity = session.query(self.model_class).filter(
                    self.model_class.id == entity_id
                ).first()
                
                if not db_entity:
                    return None
                
                for key, value in entity.items():
                    if hasattr(db_entity, key):
                        setattr(db_entity, key, value)
                
                session.commit()
                session.refresh(db_entity)
                
                result = {}
                for column in db_entity.__table__.columns:
                    result[column.name] = getattr(db_entity, column.name)
                return result
            else:
                # Use raw SQL for generic operations
                # Build SET clause
                set_clauses = []
                params = {"id": entity_id}
                
                for key, value in entity.items():
                    if key != "id":  # Don't update ID
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = value
                
                if not set_clauses:
                    return None
                
                query = f"""
                    UPDATE {self.table_name}
                    SET {", ".join(set_clauses)}
                    WHERE id = :id
                    RETURNING *
                """
                
                with ExternalApiTimer("postgresql", operation="update") as t:
                    result = session.execute(text(query), params)
                    session.commit()
                    row = result.fetchone()
                    t.set_status(status_code=200, success=(row is not None))
                
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            logger.error(f"Error updating entity: {str(e)}")
            session.rollback()
            return None

