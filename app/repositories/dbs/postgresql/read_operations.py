"""Read operations for PostgreSQL repository."""

from typing import Dict, Any, Optional, Type, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.helpers import logger, ExternalApiTimer

class PostgreSQLReadOperations:
    """Handles read operations for PostgreSQL."""
    
    def __init__(self, session_manager, model_class: Optional[Type] = None, table_name: Optional[str] = None):
        """Initialize with session manager, optional model class, and table name."""
        self.session_manager = session_manager
        self.model_class = model_class
        self.table_name = table_name or 'entities'
    
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        try:
            session = self.session_manager.get_session()
            
            if self.model_class:
                # Use SQLAlchemy model
                db_entity = session.query(self.model_class).filter(
                    self.model_class.id == entity_id
                ).first()
                
                if db_entity:
                    result = {}
                    for column in db_entity.__table__.columns:
                        result[column.name] = getattr(db_entity, column.name)
                    return result
                return None
            else:
                # Use raw SQL for generic operations
                query = f"SELECT * FROM {self.table_name} WHERE id = :id"
                
                with ExternalApiTimer("postgresql", operation="select") as t:
                    result = session.execute(text(query), {"id": entity_id})
                    row = result.fetchone()
                    t.set_status(status_code=200, success=(row is not None))
                
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving entity by ID: {str(e)}")
            return None
    
    def get_by_field(self, field_name: str, field_value: Any) -> Optional[Dict[str, Any]]:
        """Get entity by a specific field."""
        try:
            session = self.session_manager.get_session()
            
            if self.model_class:
                # Use SQLAlchemy model
                db_entity = session.query(self.model_class).filter(
                    getattr(self.model_class, field_name) == field_value
                ).first()
                
                if db_entity:
                    result = {}
                    for column in db_entity.__table__.columns:
                        result[column.name] = getattr(db_entity, column.name)
                    return result
                return None
            else:
                # Use raw SQL for generic operations
                query = f"SELECT * FROM {self.table_name} WHERE {field_name} = :value"
                
                with ExternalApiTimer("postgresql", operation="select") as t:
                    result = session.execute(text(query), {"value": field_value})
                    row = result.fetchone()
                    t.set_status(status_code=200, success=(row is not None))
                
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving entity by field: {str(e)}")
            return None
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all entities with pagination."""
        try:
            session = self.session_manager.get_session()
            
            if self.model_class:
                # Use SQLAlchemy model
                db_entities = session.query(self.model_class).offset(offset).limit(limit).all()
                
                results = []
                for db_entity in db_entities:
                    result = {}
                    for column in db_entity.__table__.columns:
                        result[column.name] = getattr(db_entity, column.name)
                    results.append(result)
                return results
            else:
                # Use raw SQL for generic operations
                query = f"SELECT * FROM {self.table_name} LIMIT :limit OFFSET :offset"
                
                with ExternalApiTimer("postgresql", operation="select") as t:
                    result = session.execute(text(query), {"limit": limit, "offset": offset})
                    rows = result.fetchall()
                    t.set_status(status_code=200, success=True)
                
                return [dict(row._mapping) for row in rows]
                
        except Exception as e:
            logger.error(f"Error listing entities: {str(e)}")
            return []
    
    def get_count(self, table_name: Optional[str] = None) -> int:
        """Get count of records in table."""
        try:
            session = self.session_manager.get_session()
            
            if self.model_class:
                count = session.query(self.model_class).count()
            else:
                table = table_name or self.table_name
                query = f"SELECT COUNT(*) as count FROM {table}"
                
                with ExternalApiTimer("postgresql", operation="count") as t:
                    result = session.execute(text(query))
                    count = result.fetchone().count
                    t.set_status(status_code=200, success=True)
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting count: {str(e)}")
            return 0

