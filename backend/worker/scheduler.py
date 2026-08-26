from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from worker.jobs import run_collection, run_interpret, run_scoring

def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_collection, CronTrigger(hour=6, minute=0), id="collect")
    scheduler.add_job(run_interpret,  CronTrigger(hour=6, minute=15), id="interpret")
    scheduler.add_job(run_scoring,    CronTrigger(hour=6, minute=30), id="score")
    return scheduler
