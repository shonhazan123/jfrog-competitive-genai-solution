from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from worker.jobs import run_collection, run_scoring

def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_collection, CronTrigger(hour=6, minute=0), id="collect")
    scheduler.add_job(run_scoring,    CronTrigger(hour=6, minute=30), id="score")

    def scheduled_digest():
        from worker.jobs import run_digest, personas_due
        from app.config.loader import load_config
        cfg = load_config()
        run_digest(personas=personas_due(cfg), cfg=cfg)

    scheduler.add_job(scheduled_digest, CronTrigger(hour=7, minute=0), id="digest")
    return scheduler
