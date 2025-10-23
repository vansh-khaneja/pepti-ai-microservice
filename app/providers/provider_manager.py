"""Provider manager for managing AI service providers globally."""

from typing import Optional
from app.providers.openai_provider import OpenAIProvider
from app.core.config import settings
from app.utils.helpers import logger


class ProviderManager:
    """Singleton manager for AI service providers."""
    
    _instance: Optional['ProviderManager'] = None
    _openai_provider: Optional[OpenAIProvider] = None
    
    def __new__(cls) -> 'ProviderManager':
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the provider manager."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all providers."""
        try:
            if settings.OPENAI_API_KEY:
                self._openai_provider = OpenAIProvider(settings.OPENAI_API_KEY)
                logger.info("OpenAI provider initialized successfully")
            else:
                logger.warning("OpenAI API key not configured")
        except Exception as e:
            logger.error(f"Failed to initialize providers: {str(e)}")
    
    @property
    def openai(self) -> OpenAIProvider:
        """Get OpenAI provider instance."""
        if self._openai_provider is None:
            raise ValueError("OpenAI provider not initialized. Check API key configuration.")
        return self._openai_provider
    
    def is_openai_available(self) -> bool:
        """Check if OpenAI provider is available."""
        return self._openai_provider is not None


# Global instance
provider_manager = ProviderManager()
