"""Relational database repository for PostgreSQL operations."""

from typing import List, Dict, Any, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.repositories.base_repository import BaseRepository
from app.core.database import SessionLocal
from app.utils.helpers import logger, ExternalApiTimer
from datetime import datetime

class RelationalRepository(BaseRepository[Dict[str, Any]]):
    """Repository for relational database operations using PostgreSQL."""
    
    def __init__(self, model_class: Optional[Type] = None):
        """Initialize with optional model class."""
        self.model_class = model_class
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
    
    def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity in the database."""
        try:
            session = self.get_session()
            
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
    
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        try:
            session = self.get_session()
            
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
                table_name = getattr(self, 'table_name', 'entities')
                query = f"SELECT * FROM {table_name} WHERE id = :id"
                
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
            session = self.get_session()
            
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
                table_name = getattr(self, 'table_name', 'entities')
                query = f"SELECT * FROM {table_name} WHERE {field_name} = :value"
                
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
    
    def update(self, entity_id: str, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an entity."""
        try:
            session = self.get_session()
            
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
                table_name = getattr(self, 'table_name', 'entities')
                
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
                    UPDATE {table_name}
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
    
    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        try:
            session = self.get_session()
            
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
                table_name = getattr(self, 'table_name', 'entities')
                query = f"DELETE FROM {table_name} WHERE id = :id"
                
                with ExternalApiTimer("postgresql", operation="delete") as t:
                    result = session.execute(text(query), {"id": entity_id})
                    session.commit()
                    t.set_status(status_code=200, success=(result.rowcount > 0))
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting entity: {str(e)}")
            session.rollback()
            return False
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all entities with pagination."""
        try:
            session = self.get_session()
            
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
                table_name = getattr(self, 'table_name', 'entities')
                query = f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset"
                
                with ExternalApiTimer("postgresql", operation="select") as t:
                    result = session.execute(text(query), {"limit": limit, "offset": offset})
                    rows = result.fetchall()
                    t.set_status(status_code=200, success=True)
                
                return [dict(row._mapping) for row in rows]
                
        except Exception as e:
            logger.error(f"Error listing entities: {str(e)}")
            return []
    
    def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query."""
        try:
            session = self.get_session()
            
            with ExternalApiTimer("postgresql", operation="raw_query") as t:
                result = session.execute(text(query), params or {})
                rows = result.fetchall()
                t.set_status(status_code=200, success=True)
            
            return [dict(row._mapping) for row in rows]
            
        except Exception as e:
            logger.error(f"Error executing raw query: {str(e)}")
            return []
    
    def get_count(self, table_name: Optional[str] = None) -> int:
        """Get count of records in table."""
        try:
            session = self.get_session()
            
            if self.model_class:
                count = session.query(self.model_class).count()
            else:
                table = table_name or getattr(self, 'table_name', 'entities')
                query = f"SELECT COUNT(*) as count FROM {table}"
                
                with ExternalApiTimer("postgresql", operation="count") as t:
                    result = session.execute(text(query))
                    count = result.fetchone().count
                    t.set_status(status_code=200, success=True)
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting count: {str(e)}")
            return 0
