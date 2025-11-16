"""Authentication utilities for API endpoints."""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.utils.helpers import logger

# HTTP Bearer token security scheme
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify Bearer token from request header.
    
    Args:
        credentials: HTTP authorization credentials containing the Bearer token
        
    Returns:
        str: The verified token
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    token = credentials.credentials
    
    # Check if API_TOKEN is configured
    if not settings.API_TOKEN:
        logger.warning("API_TOKEN not configured in settings. Authentication is disabled.")
        return token
    
    # Verify token matches configured API_TOKEN
    if token != settings.API_TOKEN:
        logger.warning(f"Invalid token attempt: {token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug("Token verified successfully")
    return token

