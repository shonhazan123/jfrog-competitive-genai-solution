from worker.jobs import run_backfill, run_seed

if __name__ == "__main__":
    run_seed()
    print(run_backfill())          # scheduler wiring arrives in Plan 2
