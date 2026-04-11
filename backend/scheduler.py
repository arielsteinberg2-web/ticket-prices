# backend/scheduler.py (stub for now — will be fully implemented in Task 7)
import logging
logger = logging.getLogger(__name__)

def run_fetch_job(db=None):
    logger.info("Fetch job called (stub)")

def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.start()
    return scheduler
