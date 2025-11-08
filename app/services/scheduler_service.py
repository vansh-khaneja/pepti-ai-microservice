"""
Scheduler service for managing cron jobs and periodic tasks
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Optional
import asyncio
from app.utils.helpers import logger


class SchedulerService:
    """Service for managing scheduled tasks (cron jobs)"""
    
    _instance: Optional['SchedulerService'] = None
    _scheduler: Optional[AsyncIOScheduler] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def scheduler(self) -> AsyncIOScheduler:
        """Get or create the scheduler instance"""
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()
        return self._scheduler
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("✅ Scheduler started successfully")
        else:
            logger.warning("Scheduler is already running")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✅ Scheduler shut down successfully")
    
    def add_cron_job(
        self,
        func,
        cron_expression: str,
        job_id: Optional[str] = None,
        **kwargs
    ):
        """
        Add a cron job using cron expression
        
        Args:
            func: Function to execute
            cron_expression: Cron expression (e.g., "0 0 * * *" for daily at midnight)
            job_id: Unique identifier for the job
            **kwargs: Additional arguments to pass to the function
        
        Cron expression format: minute hour day month day_of_week
        Examples:
            "0 0 * * *" - Every day at midnight
            "0 */6 * * *" - Every 6 hours
            "0 0 * * 0" - Every Sunday at midnight
            "*/30 * * * *" - Every 30 minutes
        """
        try:
            # Parse cron expression
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expression}. Expected format: 'minute hour day month day_of_week'")
            
            minute, hour, day, month, day_of_week = parts
            
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id or f"{func.__name__}_{cron_expression}",
                replace_existing=True,
                **kwargs
            )
            logger.info(f"✅ Added cron job: {job_id or func.__name__} with schedule: {cron_expression}")
        except Exception as e:
            logger.error(f"❌ Failed to add cron job: {e}")
            raise
    
    def add_interval_job(
        self,
        func,
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        job_id: Optional[str] = None,
        **kwargs
    ):
        """
        Add an interval-based job
        
        Args:
            func: Function to execute
            seconds: Interval in seconds
            minutes: Interval in minutes
            hours: Interval in hours
            job_id: Unique identifier for the job
            **kwargs: Additional arguments to pass to the function
        """
        try:
            # Build trigger parameters - only include non-None values
            trigger_params = {}
            if seconds is not None:
                trigger_params['seconds'] = seconds
            if minutes is not None:
                trigger_params['minutes'] = minutes
            if hours is not None:
                trigger_params['hours'] = hours
            
            # Ensure at least one interval parameter is provided
            if not trigger_params:
                raise ValueError("At least one of seconds, minutes, or hours must be provided")
            
            trigger = IntervalTrigger(**trigger_params)
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id or f"{func.__name__}_interval",
                replace_existing=True,
                **kwargs
            )
            logger.info(f"✅ Added interval job: {job_id or func.__name__}")
        except Exception as e:
            logger.error(f"❌ Failed to add interval job: {e}")
            raise
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"✅ Removed job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
    
    def get_jobs(self):
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()
    
    def pause_job(self, job_id: str):
        """Pause a scheduled job"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"✅ Paused job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to pause job {job_id}: {e}")
    
    def resume_job(self, job_id: str):
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"✅ Resumed job: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to resume job {job_id}: {e}")


# Global scheduler instance
scheduler_service = SchedulerService()

