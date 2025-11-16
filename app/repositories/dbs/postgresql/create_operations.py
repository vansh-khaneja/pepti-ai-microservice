"""Create operations for PostgreSQL repository."""

from typing import Dict, Any, Type, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.helpers import logger, ExternalApiTimer

class PostgreSQLCreateOperations:
    """Handles create operations for PostgreSQL."""
    
    def __init__(self, session_manager, model_class: Optional[Type] = None):
        """Initialize with session manager and optional model class."""
        self.session_manager = session_manager
        self.model_class = model_class
    
    def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity in the database."""
        try:
            session = self.session_manager.get_session()
            
            if self.model_class:
                # Use SQLAlchemy model
                db_entity = self.model_class(**entity)
                session.add(db_entity)
                session.commit()
                session.refresh(db_entity)
                
                # Convert to dict
                result = {}
                for column in db_entity.__table__.columns:
                    result[column.name] = getattr(db_entity, column.name)
                return result
            else:
                # Use raw SQL for generic operations
                table_name = entity.get("table_name")
                if not table_name:
                    raise ValueError("table_name is required for generic operations")
                
                columns = list(entity.keys())
                columns.remove("table_name")
                
                placeholders = ", ".join([f":{col}" for col in columns])
                column_names = ", ".join(columns)
                
                query = f"""
                    INSERT INTO {table_name} ({column_names})
                    VALUES ({placeholders})
                    RETURNING *
                """
                
                with ExternalApiTimer("postgresql", operation="insert") as t:
                    result = session.execute(text(query), entity)
                    session.commit()
                    t.set_status(status_code=200, success=True)
                
                return dict(result.fetchone()._mapping)
                
        except Exception as e:
            logger.error(f"Error creating entity: {str(e)}")
            session.rollback()
            raise

