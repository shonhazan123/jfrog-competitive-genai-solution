# Project instruction — operational flow

This folder is the operational source of truth for **how the running system works**.
Agents must base logic on these files and update them when behaviour changes.

## Run the full stack

From the repo root (Docker only):

```bash
docker compose up --build
```

Starts **db + api + worker + client**. UI at http://localhost:5173, API at http://localhost:8000.

**Boots with zero configuration.** The stack starts on any machine with just
`docker compose up --build` — no `.env` required. In `docker-compose.yml` the
`.env` file is declared `required: false` on `api` and `worker`, so a fresh
clone (where `.env` is git-ignored and absent) still comes up cleanly. `.env`
is only needed to enable **Run now** live gathering (`OPENAI_API_KEY`) and,
optionally, email digests (`SMTP_USER` / `SMTP_APP_PASSWORD`). OpenAI clients
are instantiated lazily (only when a run executes), so a keyless boot never
crashes the api or worker. See the root [README.md](../../README.md) and
[.env.example](../../.env.example) for setup.

The shipped compose keeps only the mounts needed to run the product
(`config`, `blobs`, and the worker's `fixtures/wayback`). Test-only mounts
(`/var/run/docker.sock`, `./tests`, `./client`) and testcontainers env are not
in it, so boot doesn't depend on host paths that differ across machines.
`.dockerignore` files in `backend/` and `client/` keep host artifacts
(`node_modules`, `.venv`, caches, `data/blobs`) out of the images.

On startup, **api** and **worker** each run `alembic upgrade head` (via `backend/docker-entrypoint.sh`)
before uvicorn or the worker process starts, so the Postgres volume always matches the code.
The worker seeds the registry but **does not** replay Wayback backfill on boot by default
(`BACKFILL_ON_START=false`; change-detection is benched). Set `BACKFILL_ON_START=true` on the
worker service to opt into offline archive replay — missing fixtures for a snapshot source are
logged and skipped rather than crashing the worker.

- `docker compose down` — stop everything
- `docker compose down -v` — stop and wipe the database volume (start clean)
- `docker compose logs -f` — follow logs

Do not run `npm run dev` in `client/` separately — only the Docker client on :5173.

### First run (empty database → instructive onboarding)

On a fresh machine the database is empty. In **live** mode the consumer pages do
**not** seed React Query with fixture data; instead each renders an instructive
empty state guiding the user to click **Run now** (which triggers `POST /runs/all`).
See [client.md](./client.md) for the per-page onboarding behaviour.

Design intent (problem, requirements, build plan) stays in [PRD.md](../PRD.md),
[DESIGN.md](../DESIGN.md), and [ARCHITECTURE.md](../ARCHITECTURE.md). The HTTP
shapes live in [API_CONTRACT.md](../API_CONTRACT.md). Implementation plans in
[plans/](../plans/) are historical; do not rewrite them when code diverges — update
this folder instead.

The system is **verdict-first**: consumer screens show a tier word + one-line
reason backed by a clickable source, with no numbers and no historical diffing.
Numeric scoring and change-detection (backfill / `ClaimVersion` / Trajectory /
`ClaimTimeline`) still exist internally but are off every primary surface.

| File | Covers |
|---|---|
| [digests.md](./digests.md) | `GET /digests/{persona}` vs `GET /digests/exec/weekly`; tier-based ranking |
| [comparison.md](./comparison.md) | `GET /comparison/matrix` component × competitor stance grid (no numbers, no diff) |
| [config.md](./config.md) | Intention-based Settings (`/config/competitors`, `/config/instructions`), tier thresholds |
| [runs.md](./runs.md) | `POST /runs` async progress, `GET /runs/{id}`, human stages |
| [kits.md](./kits.md) | `GET /kits`, KIT rollup, citations, display labels (backend only; grid retired) |
| [ask.md](./ask.md) | Ask graph routing, hit accumulation, `POST /ask` bridge |
| [agent.md](./agent.md) | Interpret/Ask graph step logging and failure signals |
| [llm.md](./llm.md) | Per-call LLM tuning via `config/llm.yaml`, `get_model` wiring, env overrides |
| [client.md](./client.md) | React client: verdict-first IA, fixture/live switch, tokens, SignalCard rule, live-wiring contract drift |
| [industry.md](./industry.md) | Industry feed + stable themes (`/industry/themes`), JFrog-relevance lines |
| [maintenance.md](./maintenance.md) | `python -m app.services.maintenance` — purge findings, keep registry + captures |
