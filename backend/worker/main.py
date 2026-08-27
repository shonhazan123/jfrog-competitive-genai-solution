from app.logging_config import setup_logging
from app.settings import settings
from worker.jobs import run_backfill, run_seed
from worker.scheduler import build_scheduler

if __name__ == "__main__":
    setup_logging()
    run_seed()
    if settings.backfill_on_start:
        print(run_backfill())
    scheduler = build_scheduler()
    scheduler.start()
