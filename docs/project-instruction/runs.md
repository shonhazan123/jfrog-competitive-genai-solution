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
| `manual` | **Run now** — forced collect + interpret (up to 6 pending captures) + score |
| `collect` | `run_collection` at **Checking sources** |
| `interpret` | `run_interpret` at **Extracting claims** |
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
`interpret.capture.*`, `interpret.batch.failed`, `sanitize.*`, `extract.*`, `verify.*`
(agent/worker). A single capture timing out on `extract` logs `extract.failed` and
`interpret.batch.failed` but no longer aborts the whole run — check `failed` in the
interpret job report. Set `LOG_LEVEL=DEBUG` in `.env` for model-selection detail.
See [agent.md](./agent.md) and [llm.md](./llm.md) for timeout tuning.

## Unchanged endpoints

- `POST /runs/collect` — synchronous collection (scheduler path)
- `GET /runs/status` — last/next scheduled run counters
- `GET /runs/latest` — funnel strip for Today (latest run summary)
