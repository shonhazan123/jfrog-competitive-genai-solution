# Offline fixture-backed backfill

The Day-1 milestone replays Sonatype comparison-page history from the Internet Archive. On networks that cannot reach `web.archive.org`, use committed fixtures so `docker compose up` runs entirely offline.

## Two phases

### 1. Capture (once, from a network with Archive access)

Run from a machine or VPN that can reach `web.archive.org`. This records the exact CDX query URLs and snapshot HTML bodies the pipeline requests at replay time.

#### Fetch fixtures on the host (no Docker)

Use this when VPN works on the host but **not** inside Docker containers. The tool uses the host network (stdlib Python only — no `pip install`, no `app` imports), writes `fixtures/wayback/manifest.json` plus `.bin` files, and keys each entry with the same URLs `wayback.py` builds at replay time.

```powershell
# From repo root; VPN must be on
python tools/fetch_fixtures_local.py
```

Optional URL override (defaults to snapshot sources in `config/sources.yaml`):

```powershell
python tools/fetch_fixtures_local.py "https://www.sonatype.com/compare/sonatype-nexus-versus-jfrog-artifactory"
```

This is the **only** step that needs Internet Archive access. Commit the resulting `fixtures/wayback/` files so every developer and demo environment can replay offline.

#### Other capture options

**Outside Docker** (local venv with backend installed):

```powershell
cd backend
pip install -e .
python -m scripts.capture_wayback
```

**Inside Docker on VPN**:

```powershell
docker compose run --rm worker python -m scripts.capture_wayback
```

### 2. Replay (offline, default)

After fixtures are committed, inject them into Postgres and check stats (no Archive access needed):

```powershell
docker compose up -d db
docker compose run --rm worker python -m worker.main
docker compose up -d api
Invoke-WebRequest -UseBasicParsing http://localhost:8000/stats | Select-Object -ExpandProperty Content
```

Or start everything at once:

```powershell
docker compose up
```

The worker uses `BACKFILL_SOURCE=fixtures` (set in `docker-compose.yml`) and `FixtureFetcher` over `fixtures/wayback/`. No robots check or live HTTP calls are made during replay.

### Switch back to live backfill

Set `BACKFILL_SOURCE=live` on the worker service (or export it before `docker compose up`). The worker will use `StaticFetcher` and `RobotsCache` as before.

## Why this works

`RecordingFetcher` keys fixtures by the **exact request URL** (`list_snapshots` CDX query and each `Snapshot.raw_url`). `FixtureFetcher` replays those same URLs through the unchanged `backfill_source` pipeline (fetch → parse → diff → claims).
