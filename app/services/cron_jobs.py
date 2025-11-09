"""
Cron job definitions - Add your scheduled tasks here
"""
from datetime import datetime, timedelta
from app.utils.helpers import logger
from app.core.database import SessionLocal


async def cleanup_old_sessions():
    """
    Cleanup old chat sessions and peptide info sessions
    Runs daily at 2 AM
    """
    try:
        logger.info("🧹 Starting cleanup of old sessions...")
        from app.models.chat_session import ChatSession
        from app.models.peptide_info_session import PeptideInfoSession
        
        db = SessionLocal()
        try:
            # Delete sessions older than 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            # Delete old chat sessions
            deleted_chat = db.query(ChatSession).filter(
                ChatSession.created_at < cutoff_date
            ).delete()
            
            # Delete old peptide info sessions
            deleted_peptide = db.query(PeptideInfoSession).filter(
                PeptideInfoSession.created_at < cutoff_date
            ).delete()
            
            db.commit()
            logger.info(f"✅ Cleaned up {deleted_chat} old chat sessions and {deleted_peptide} peptide info sessions")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error during session cleanup: {e}")
            raise
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Failed to cleanup old sessions: {e}")


async def cleanup_redis_cache():
    """
    Cleanup expired cache entries in Redis
    Runs every 6 hours
    """
    try:
        logger.info("🧹 Starting Redis cache cleanup...")
        from app.repositories.repository_manager import repository_manager
        
        # Redis automatically handles TTL expiration, but we can log cache stats
        cache_repo = repository_manager.cache
        if hasattr(cache_repo, 'get_cache_stats'):
            stats = cache_repo.get_cache_stats()
            logger.info(f"📊 Redis cache stats: {stats}")
        else:
            logger.info("✅ Redis cache cleanup check completed (TTL handled automatically)")
    except Exception as e:
        logger.error(f"❌ Failed to cleanup Redis cache: {e}")


async def aggregate_daily_analytics():
    """
    Aggregate daily analytics data
    Runs daily at 1 AM
    """
    try:
        logger.info("📊 Starting daily analytics aggregation...")
        from app.services.analytics_service import AnalyticsService
        
        db = SessionLocal()
        try:
            analytics_service = AnalyticsService(db)
            # Add any aggregation logic here if needed
            # For now, just log that the job ran
            logger.info("✅ Daily analytics aggregation completed")
        except Exception as e:
            logger.error(f"❌ Error during analytics aggregation: {e}")
            raise
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Failed to aggregate daily analytics: {e}")


async def health_check_job():
    """
    Periodic health check job
    Runs every 2 hours
    """
    try:
        logger.info("🏥 Running health check...")
        from app.core.database import SessionLocal
        from app.repositories.repository_manager import repository_manager
        
        # Check database connection
        db = SessionLocal()
        try:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            logger.info("✅ Database health check: OK")
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
        finally:
            db.close()
        
        # Check Redis connection
        try:
            cache_repo = repository_manager.cache
            if cache_repo and hasattr(cache_repo, 'ping'):
                cache_repo.ping()
                logger.info("✅ Redis health check: OK")
            else:
                logger.warning("⚠️ Redis repository not available or ping method missing")
        except Exception as e:
            logger.warning(f"⚠️ Redis health check failed: {e}")
        
        # Check Qdrant connection
        try:
            vector_repo = repository_manager.vector_store
            if vector_repo and hasattr(vector_repo, 'health_check'):
                vector_repo.health_check()
                logger.info("✅ Qdrant health check: OK")
            else:
                logger.warning("⚠️ Qdrant repository not available or health_check method missing")
        except Exception as e:
            logger.warning(f"⚠️ Qdrant health check failed: {e}")
            
    except Exception as e:
        logger.error(f"❌ Health check job failed: {e}")


async def cleanup_old_analytics():
    """
    Cleanup old analytics data (keep last 1 year)
    Runs weekly on Sunday at 3 AM
    """
    try:
        logger.info("🧹 Starting cleanup of old analytics data...")
        from app.models.analytics import ExternalApiUsage
        
        db = SessionLocal()
        try:
            # Delete analytics older than 1 year
            cutoff_date = datetime.utcnow() - timedelta(days=365)
            
            deleted = db.query(ExternalApiUsage).filter(
                ExternalApiUsage.created_at < cutoff_date
            ).delete()
            
            db.commit()
            logger.info(f"✅ Cleaned up {deleted} old analytics records")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error during analytics cleanup: {e}")
            raise
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Failed to cleanup old analytics: {e}")


async def sync_peptides_from_supabase():
    """
    Sync peptides from Supabase to Qdrant vector database
    Fetches data, compares with previous CSV, and adds only new peptides
    Runs every 2 minutes (for testing)
    """
    try:
        logger.info("🔄 Starting Supabase peptide sync job...")
        import asyncio
        from app.services.supabase_sync_service import SupabaseSyncService
        
        sync_service = SupabaseSyncService()
        # Run sync in thread since it uses synchronous libraries (pandas, supabase)
        await asyncio.to_thread(sync_service.sync_peptides)
        
        logger.info("✅ Supabase peptide sync job completed")
    except Exception as e:
        logger.error(f"❌ Supabase peptide sync job failed: {e}")
        # Don't raise - allow job to continue on next run

