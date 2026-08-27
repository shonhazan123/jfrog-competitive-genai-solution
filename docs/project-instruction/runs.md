# Runs — async pipeline progress

**Startup:** `api` and `worker` containers run `alembic upgrade head` on boot (see
`backend/docker-entrypoint.sh`) so schema matches models before any run job touches Postgres.
Both may start migrations concurrently; `backend/alembic/env.py` serializes them with a Postgres
session advisory lock (`MIGRATION_LOCK_KEY`) so only one container applies revisions at a time.
The worker seeds sources but skips Wayback backfill unless `BACKFILL_ON_START=true` (verdict-first:
change-detection is benched). When backfill is enabled with `BACKFILL_SOURCE=fixtures`, a snapshot
source with no committed Wayback fixture is skipped with a warning — it does not fail the worker or
`POST /runs`.

Manual and scheduled runs share the same worker jobs (`worker.jobs`). The in-memory
run store holds **multiple concurrent runs** (each with a unique
`run_{timestamp}_{uuid}` id). There is no persisted run history beyond what
`GET /runs/latest` reports from the last completed collection.

## `POST /runs`

Starts a background run and returns immediately:

- Status **202**
- Body: `{ "run_id": "run_2026-08-27T17:55:00Z_a1b2c3" }` (surface kinds also return `"kind"`)

`kind` selects which job runs:

| `kind` | Job |
|---|---|
| `industry` | `run_industry` — Industry research agent (four DevSecOps buckets) |
| `signals` | `run_signals` — Signals research agent (competitor sub-types + OSV) |
| `comparison` | `run_comparison` — Comparison grid agent (25 cells, Claim+stance) |
| `manual` | forced collect + score (legacy path) |
| `collect` | `run_collection` at **Checking sources** |
| `scoring` | `run_scoring` at legacy score stage |

## `POST /runs/all`

Fans out three surface runs concurrently — one `run_id` per surface:

```json
{ "run_ids": { "industry": "...", "signals": "...", "comparison": "..." } }
```

Each surface run is tracked independently; one failure does not fail the others.

Human stage labels come from `config/run_stages.yaml` (research-oriented stages:
collect → research → synthesize → done).

## Worker jobs — collection and scoring

`run_collection` and `run_scoring` live in `worker.jobs`. Tests pass an
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

Manual (`force=True`) collection applies a 30-day window on feed and API entries
so old backlog does not flood captures on a **Run now**.

### `run_scoring`

`run_scoring` reloads materiality config and updates `score_sales`, `score_product`,
and `score_exec` on every `Signal` row. It runs serially on the caller's session
or opens its own when invoked from the worker.

## `GET /runs/{run_id}`

Poll progress for the current run:

```json
{
  "run_id": "run_2026-08-26T06:00Z",
  "status": "running",
  "stage_label": "Researching",
  "progress": { "current": 1, "total": 4 },
  "new_items": 0,
  "message": ""
}
```

- `stage_label` is always a human label from `run_stages.yaml` (never a key like `collect`).
- `status`: `running` | `done` | `failed`
- On `done`, `new_items` reflects captures / scored counts from the job report.
- On `failed`, `message` is plain language (no tracebacks).

## Debugging with logs

Background runs and agent steps log to stdout. Tail them with:

```bash
docker compose logs -f api worker
```

Key lines: `run.start`, `run.stage`, `run.job.done`, `run.failed` (API);
`collection.done`, `sanitize.*` (worker). Set `LOG_LEVEL=DEBUG` in `.env` for
model-selection detail. See [agent.md](./agent.md) and [llm.md](./llm.md) for
timeout tuning.

## Unchanged endpoints

- `POST /runs/collect` — synchronous collection (scheduler path)
- `GET /runs/status` — last/next scheduled run counters
- `GET /runs/latest` — funnel strip for Today (latest run summary)
