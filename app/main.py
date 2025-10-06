from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db, close_db
# from app.middleware.analytics_middleware import AnalyticsMiddleware
from app.utils.helpers import logger

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Analytics middleware (disabled per request)
# app.add_middleware(AnalyticsMiddleware)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Pepti Wiki AI API", "status": "active"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pepti-wiki-ai"}

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        # Import models to ensure they're registered with SQLAlchemy
        from app.models import (
            ChatSession, ChatMessage,
            PeptideInfoSession, PeptideInfoMessage,
            ExternalApiUsage
        )
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {str(e)}")
        logger.warning("Analytics functionality will not be available")
        logger.warning("Please check your database connection and restart the application")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    try:
        close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.warning(f"Error closing database connection: {str(e)}")
