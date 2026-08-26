# Runs — async pipeline progress

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
| `collect` | `run_collection` at **Checking sources** |
| `interpret` | `run_interpret` at **Extracting claims** |
| `scoring` | `run_scoring` at **Scoring and routing** |

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

## Unchanged endpoints

- `POST /runs/collect` — synchronous collection (scheduler path)
- `GET /runs/status` — last/next scheduled run counters
- `GET /runs/latest` — funnel strip for Today (latest run summary)
