"""Qdrant client initialization and configuration."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings
from app.utils.helpers import logger

class QdrantClientManager:
    """Manages Qdrant client initialization and collection setup."""
    
    def __init__(self):
        """Initialize Qdrant client."""
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(settings.QDRANT_URL)
            
            if settings.QDRANT_API_KEY:
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY
                )
            else:
                self.client = QdrantClient(url=settings.QDRANT_URL)
            
            self.collection_name = settings.PEPTIDE_COLLECTION
            self.vector_size = 3072  # OpenAI text-embedding-3-large dimension
            
            # Ensure collection exists
            self._ensure_collection_exists()
            logger.info("Qdrant client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {str(e)}")
            raise
    
    def _ensure_collection_exists(self):
        """Ensure the peptides collection exists, create if it doesn't."""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection '{self.collection_name}' created successfully")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            raise

