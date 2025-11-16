"""Main PostgreSQL repository that composes all operation modules."""

from typing import Dict, Any, List, Optional, Type
from app.repositories.base.base_repository import BaseRepository
from .session import PostgreSQLSessionManager
from .create_operations import PostgreSQLCreateOperations
from .read_operations import PostgreSQLReadOperations
from .update_operations import PostgreSQLUpdateOperations
from .delete_operations import PostgreSQLDeleteOperations
from .query_operations import PostgreSQLQueryOperations

class RelationalRepository(BaseRepository[Dict[str, Any]]):
    """Repository for relational database operations using PostgreSQL."""
    
    def __init__(self, model_class: Optional[Type] = None):
        """Initialize PostgreSQL repository with all operation modules."""
        self.model_class = model_class
        
        # Initialize session manager
        self.session_manager = PostgreSQLSessionManager()
        
        # Initialize operation modules
        self.create_ops = PostgreSQLCreateOperations(self.session_manager, model_class)
        self.read_ops = PostgreSQLReadOperations(self.session_manager, model_class)
        self.update_ops = PostgreSQLUpdateOperations(self.session_manager, model_class)
        self.delete_ops = PostgreSQLDeleteOperations(self.session_manager, model_class)
        self.query_ops = PostgreSQLQueryOperations(self.session_manager)
    
    # BaseRepository interface methods
    def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity."""
        return self.create_ops.create(entity)
    
    def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID."""
        return self.read_ops.get_by_id(entity_id)
    
    def update(self, entity_id: str, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an entity."""
        return self.update_ops.update(entity_id, entity)
    
    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        return self.delete_ops.delete(entity_id)
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List all entities with pagination."""
        return self.read_ops.list_all(limit, offset)
    
    # Additional PostgreSQL-specific methods
    def get_session(self):
        """Get database session."""
        return self.session_manager.get_session()
    
    def close_session(self):
        """Close database session."""
        return self.session_manager.close_session()
    
    def get_by_field(self, field_name: str, field_value: Any) -> Optional[Dict[str, Any]]:
        """Get entity by a specific field."""
        return self.read_ops.get_by_field(field_name, field_value)
    
    def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query."""
        return self.query_ops.execute_raw_query(query, params)
    
    def get_count(self, table_name: Optional[str] = None) -> int:
        """Get count of records in table."""
        return self.read_ops.get_count(table_name)

