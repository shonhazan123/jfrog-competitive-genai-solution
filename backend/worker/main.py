from app.logging_config import setup_logging
from worker.jobs import run_seed
from worker.scheduler import build_scheduler

if __name__ == "__main__":
    setup_logging()
    run_seed()
    scheduler = build_scheduler()
    scheduler.start()
