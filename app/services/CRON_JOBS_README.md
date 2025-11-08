# Cron Jobs Documentation

This FastAPI application now supports cron jobs using APScheduler (Advanced Python Scheduler).

## Installation

After adding `apscheduler==3.10.4` to `requirements.txt`, install it:

```bash
pip install -r requirements.txt
```

## How It Works

The scheduler is automatically initialized when the FastAPI application starts and shuts down gracefully when the application stops.

## Pre-configured Jobs

The following cron jobs are automatically registered:

1. **cleanup_old_sessions** - Daily at 2 AM
   - Cleans up chat sessions and peptide info sessions older than 90 days

2. **aggregate_daily_analytics** - Daily at 1 AM
   - Aggregates daily analytics data

3. **cleanup_old_analytics** - Weekly on Sunday at 3 AM
   - Cleans up analytics data older than 1 year

4. **cleanup_redis_cache** - Every 6 hours
   - Checks Redis cache status (TTL is handled automatically by Redis)

5. **health_check_job** - Every 30 minutes
   - Performs health checks on database, Redis, and Qdrant connections

## Adding New Cron Jobs

### Method 1: Add to `cron_jobs.py`

1. Create a new async function in `app/services/cron_jobs.py`:

```python
async def my_custom_job():
    """My custom job description"""
    try:
        logger.info("Running my custom job...")
        # Your job logic here
        logger.info("✅ Custom job completed")
    except Exception as e:
        logger.error(f"❌ Custom job failed: {e}")
```

2. Register it in `app/main.py` in the `startup_event()` function:

```python
# Add after other job registrations
scheduler_service.add_cron_job(
    cron_jobs.my_custom_job,
    cron_expression="0 */4 * * *",  # Every 4 hours
    job_id="my_custom_job"
)
```

### Method 2: Cron Expression Format

Cron expressions use the format: `minute hour day month day_of_week`

Examples:
- `"0 0 * * *"` - Every day at midnight
- `"0 */6 * * *"` - Every 6 hours
- `"0 0 * * 0"` - Every Sunday at midnight
- `"*/30 * * * *"` - Every 30 minutes
- `"0 9 * * 1-5"` - Every weekday at 9 AM
- `"0 0 1 * *"` - First day of every month at midnight

### Method 3: Interval-Based Jobs

For jobs that run at regular intervals:

```python
scheduler_service.add_interval_job(
    cron_jobs.my_job,
    minutes=15,  # Every 15 minutes
    job_id="my_interval_job"
)

# Or use hours
scheduler_service.add_interval_job(
    cron_jobs.my_job,
    hours=2,  # Every 2 hours
    job_id="my_hourly_job"
)
```

## Managing Jobs Programmatically

You can manage jobs at runtime using the scheduler service:

```python
from app.services.scheduler_service import scheduler_service

# Get all jobs
jobs = scheduler_service.get_jobs()

# Pause a job
scheduler_service.pause_job("my_job_id")

# Resume a job
scheduler_service.resume_job("my_job_id")

# Remove a job
scheduler_service.remove_job("my_job_id")
```

## Best Practices

1. **Error Handling**: Always wrap your job logic in try-except blocks
2. **Logging**: Use the logger to track job execution
3. **Database Sessions**: Always close database sessions in finally blocks
4. **Async Functions**: All job functions should be async
5. **Idempotency**: Design jobs to be safe if they run multiple times

## Testing Cron Jobs

To test a cron job manually, you can call it directly:

```python
from app.services import cron_jobs
import asyncio

# Run the job
asyncio.run(cron_jobs.cleanup_old_sessions())
```

Or create a test endpoint in your API:

```python
@app.post("/test-cron-job")
async def test_cron_job(job_name: str):
    """Test endpoint to manually trigger cron jobs"""
    from app.services import cron_jobs
    
    if hasattr(cron_jobs, job_name):
        job_func = getattr(cron_jobs, job_name)
        await job_func()
        return {"message": f"Job {job_name} executed successfully"}
    else:
        return {"error": f"Job {job_name} not found"}
```

## Monitoring

All cron job executions are logged. Check your application logs to monitor:
- Job start times
- Job completion status
- Any errors that occur

## Notes

- The scheduler runs in the same process as your FastAPI application
- Jobs are executed asynchronously and won't block the main application
- If a job fails, it won't affect other jobs or the main application
- The scheduler automatically handles timezone (uses UTC by default)

