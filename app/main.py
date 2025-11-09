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

def _initialize_cost_calculator_background():
    """Background task to initialize cost calculator"""
    try:
        from app.services.cost_calculator import _get_cost_calculator
        _ = _get_cost_calculator()
        logger.info("Cost calculator initialized in background")
    except Exception as e:
        logger.warning(f"Cost calculator initialization failed (non-critical): {str(e)}")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup, other services in background"""
    try:
        # Set server start time
        from app.core.server_info import set_server_start_time
        set_server_start_time()
        
        # Import models to ensure they're registered with SQLAlchemy
        from app.models import (
            ChatSession, ChatMessage,
            PeptideInfoSession, PeptideInfoMessage,
            ExternalApiUsage
        )
        init_db()
        logger.info("Database initialized successfully")
        
        # Initialize cost calculator in background (non-blocking)
        import asyncio
        asyncio.create_task(asyncio.to_thread(_initialize_cost_calculator_background))
        
        # Repositories (Redis, Qdrant) will initialize lazily on first access
        # This allows the app to start quickly even if external services are temporarily unavailable
        logger.info("Repositories will initialize on first access (lazy initialization)")
        
        # Initialize and start scheduler for cron jobs
        try:
            from app.services.scheduler_service import scheduler_service
            from app.services import cron_jobs
            
            scheduler_service.start()
            
            # Register cron jobs
            # Daily cleanup of old sessions at 2 AM
            scheduler_service.add_cron_job(
                cron_jobs.cleanup_old_sessions,
                cron_expression="0 2 * * *",  # Daily at 2 AM
                job_id="cleanup_old_sessions"
            )
            
            # Daily analytics aggregation at 1 AM
            scheduler_service.add_cron_job(
                cron_jobs.aggregate_daily_analytics,
                cron_expression="0 1 * * *",  # Daily at 1 AM
                job_id="aggregate_daily_analytics"
            )
            
            # Weekly cleanup of old analytics on Sunday at 3 AM
            scheduler_service.add_cron_job(
                cron_jobs.cleanup_old_analytics,
                cron_expression="0 3 * * 0",  # Sunday at 3 AM
                job_id="cleanup_old_analytics"
            )
            
            # Redis cache cleanup every 6 hours
            scheduler_service.add_interval_job(
                cron_jobs.cleanup_redis_cache,
                hours=6,
                job_id="cleanup_redis_cache"
            )
            
            # Health check every 2 minutes
            scheduler_service.add_interval_job(
                cron_jobs.health_check_job,
                minutes=2,
                job_id="health_check_job"
            )
            
            # Supabase peptide sync every 6 hours
            scheduler_service.add_interval_job(
                cron_jobs.sync_peptides_from_supabase,
                hours=6,
                job_id="sync_peptides_from_supabase"
            )
            
            logger.info("✅ All cron jobs registered successfully")
        except Exception as e:
            logger.warning(f"Scheduler initialization failed (non-critical): {str(e)}")
            logger.warning("Cron jobs will not be available, but the application will continue to run")
            
    except Exception as e:
        logger.warning(f"Database initialization failed: {str(e)}")
        logger.warning("Analytics functionality will not be available")
        logger.warning("Please check your database connection and restart the application")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    try:
        # Shutdown scheduler
        try:
            from app.services.scheduler_service import scheduler_service
            scheduler_service.shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down scheduler: {str(e)}")
        
        # Close database connection
        close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.warning(f"Error closing database connection: {str(e)}")
