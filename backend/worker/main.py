from worker.jobs import run_backfill, run_seed
from worker.scheduler import build_scheduler

if __name__ == "__main__":
    run_seed()
    print(run_backfill())
    scheduler = build_scheduler()
    scheduler.start()
