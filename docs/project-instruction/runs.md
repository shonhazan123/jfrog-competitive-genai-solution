# Runs — async pipeline progress

**Startup:** `api` and `worker` containers run `alembic upgrade head` on boot (see
`backend/docker-entrypoint.sh`) so schema matches models before any run job touches Postgres.
The worker seeds sources but skips Wayback backfill unless `BACKFILL_ON_START=true` (verdict-first:
change-detection is benched). When backfill is enabled with `BACKFILL_SOURCE=fixtures`, a snapshot
source with no committed Wayback fixture is skipped with a warning — it does not fail the worker or
`POST /runs`.

Manual and scheduled runs share the same worker jobs (`worker.jobs`). The demo keeps
**only the current run** in memory — there is no run history or persistence of past
progress beyond what `GET /runs/latest` reports from the last completed collection.

## `POST /runs`

Starts a background run and returns immediately:

- Status **202**
- Body: `{ "run_id": "run_2026-08-26T06:00Z" }`

`kind` selects which job runs at its mapped stage:

| `kind` | Job (at stage) |
|---|---|
| `manual` | **Run now** — forced collect + score |
| `collect` | `run_collection` at **Checking sources** |
| `scoring` | `run_scoring` at **Scoring and routing** |

### Interpret capture selection is source-diversified

`run_interpret` does **not** drain pending captures in raw id order. It round-robins
across their sources (`_diversify_by_source`), and drains sources that have **not yet
produced any signal** first. Within a single source the oldest-first id order is
preserved. This stops one backlogged source (e.g. hundreds of `sonatype_compare_jfrog`
snapshots) from monopolising the `limit` budget and starving every other screen — a
`manual` run now lights up new sources (industry, talent, sentiment) instead of emitting
another near-duplicate of the same competitor-comparison signal.

Dispatch uses FastAPI `BackgroundTasks` so Starlette's `TestClient` runs the job
synchronously before the response returns (spy tests), while uvicorn serves the 202
immediately and runs the job in a thread pool.

Human stage labels come from `config/run_stages.yaml` (not loaded via `schema.py`).

## Worker jobs — collection and interpret

`run_collection` and `run_interpret` live in `worker.jobs`. Tests pass an
injected SQLAlchemy `Session` and run **single-threaded** (existing behaviour
preserved). Production / manual runs open their own sessions and may fan out
work in parallel — **never sharing one `Session` across threads**.

### `run_collection` — parallel by domain

When `run_collection` opens its own session (`session=None`), sources are grouped
by URL netloc. Each domain group runs in a `ThreadPoolExecutor` (`max_workers=8`
default); sources within a domain still run serially so per-domain rate limits
hold. Each worker thread opens its own `SessionLocal()` and commits before
returning. The injected-session path (tests, synchronous `POST /runs/collect`)
iterates sources serially on the caller's session.

### `run_interpret` — dedup, empty skip, parallel captures

`run_interpret` report keys:

| key | meaning |
|---|---|
| `interpreted` | Captures that produced a persisted Signal (`status == "ok"`) |
| `quarantined` | Max repairs exhausted |
| `failed` | Per-capture exception (does not abort the batch) |
| `skipped_empty` | Zero verified claims after extract/verify — graph routed to `finalize_empty`, no Signal written |
| `skipped_duplicate` | Pending capture dropped because its `content_hash` already has interpreted evidence |

Before interpret, pending captures are **source-diversified** (see above), then
**content-hash deduped**: if a hash already appears on any `SignalEvidence` row,
later pending captures with the same hash are skipped (`skipped_duplicate`).
Among remaining pending captures, only the first occurrence of each new hash is
interpreted.

When `run_interpret` opens its own session (`session=None`), capture ids are
processed in a `ThreadPoolExecutor` (`max_workers=3` default); each worker
calls `interpret_capture` with a fresh `SessionLocal()`. The injected-session
path (all current `test_jobs` cases) stays serial on the caller's session.

## `GET /runs/{run_id}`

Poll progress for the current run:

```json
{
  "run_id": "run_2026-08-26T06:00Z",
  "status": "running",
  "stage_label": "Reading new documents",
  "progress": { "current": 1, "total": 5 },
  "new_items": 0,
  "message": ""
}
```

- `stage_label` is always a human label from `run_stages.yaml` (never a key like `collect`).
- `status`: `running` | `done` | `failed`
- On `done`, `new_items` reflects captures / interpreted / scored counts from the job report.
- On `failed`, `message` is plain language (no tracebacks).

## Debugging with logs

Background runs and agent steps log to stdout. Tail them with:

```bash
docker compose logs -f api worker
```

Key lines: `run.start`, `run.stage`, `run.job.done`, `run.failed` (API);
`interpret.capture.*`, `interpret.batch.failed`, `interpret.batch.done`
(includes `skipped_empty` / `skipped_duplicate` when non-zero), `sanitize.*`,
`extract.*`, `verify.*` (agent/worker). A single capture timing out on `extract`
logs `extract.failed` and `interpret.batch.failed` but no longer aborts the whole
run — check `failed`, `skipped_empty`, and `skipped_duplicate` in the interpret
job report. Set `LOG_LEVEL=DEBUG` in `.env` for model-selection detail.
See [agent.md](./agent.md) and [llm.md](./llm.md) for timeout tuning.

## Unchanged endpoints

- `POST /runs/collect` — synchronous collection (scheduler path)
- `GET /runs/status` — last/next scheduled run counters
- `GET /runs/latest` — funnel strip for Today (latest run summary)
