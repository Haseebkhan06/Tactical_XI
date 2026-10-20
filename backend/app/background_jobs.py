from datetime import datetime, timezone
import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def refresh_analysis_cache():
    """
    Scheduled job placeholder.

    Next, we'll connect this job to Tactical_XI's existing
    pressing-analysis logic and cache the results.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Tactical_XI background job executed at %s",
        timestamp,
    )


def start_scheduler():
    """Start the scheduler once, if it is not already running."""
    if not scheduler.running:
        scheduler.add_job(
            refresh_analysis_cache,
            trigger="interval",
            minutes=15,
            id="refresh_analysis",
            replace_existing=True,
            max_instances=1,
        )

        scheduler.start()
        logger.info("Tactical_XI scheduler started")


def stop_scheduler():
    """Stop the scheduler when the application shuts down."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Tactical_XI scheduler stopped")