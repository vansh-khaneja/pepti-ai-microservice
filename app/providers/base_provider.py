"""Base provider interface for AI services."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseProvider(ABC):
    """Base class for all AI service providers."""
    
    def __init__(self, api_key: str):
        """Initialize the provider with API key."""
        self.api_key = api_key
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text."""
        pass
    
    @abstractmethod
    def generate_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate chat completion response."""
        pass
    
    @abstractmethod
    def generate_response(self, input_text: str, **kwargs) -> str:
        """Generate response using the responses API."""
        pass
