"""Base repository interface for data access."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generic, TypeVar

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base class for all repositories."""
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def update(self, entity_id: str, entity: T) -> Optional[T]:
        """Update an entity."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        pass
    
    @abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List all entities with pagination."""
        pass
