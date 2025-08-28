from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Pepti Wiki AI"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered peptide information and search API"
    API_V1_STR: str = "/api/v1"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # CORS settings
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/pepti_wiki"
    DATABASE_NAME: str = "pepti_wiki"
    
    # Qdrant settings
    QDRANT_URL: str = "https://827cd0ad-0136-428d-aa69-a0086eb93e7d.eu-west-1-0.aws.cloud.qdrant.io:6333"
    QDRANT_API_KEY: str = ""  # Add your Qdrant cloud API key if required
    PRODUCT_COLLECTION: str = "products"
    FAQ_COLLECTION: str = "faqs"
    PEPTIDE_COLLECTION: str = "peptides"
    
    # API Keys
    SERP_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
