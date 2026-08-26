# Offline fixture-backed backfill

The Day-1 milestone replays Sonatype comparison-page history from the Internet Archive. On networks that cannot reach `web.archive.org`, use committed fixtures so `docker compose up` runs entirely offline.

## Two phases

### 1. Capture (once, from a network with Archive access)

Run from a machine or VPN that can reach `web.archive.org`. This records the exact CDX query URLs and snapshot HTML bodies the pipeline requests at replay time.

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

Output is written to `fixtures/wayback/` (`manifest.json` plus `.bin` files). Commit those files so every developer and demo environment can replay without network access.

### 2. Replay (offline, default)

```powershell
docker compose up
```

The worker uses `BACKFILL_SOURCE=fixtures` (set in `docker-compose.yml`) and `FixtureFetcher` over `fixtures/wayback/`. No robots check or live HTTP calls are made during replay.

### Switch back to live backfill

Set `BACKFILL_SOURCE=live` on the worker service (or export it before `docker compose up`). The worker will use `StaticFetcher` and `RobotsCache` as before.

## Why this works

`RecordingFetcher` keys fixtures by the **exact request URL** (`list_snapshots` CDX query and each `Snapshot.raw_url`). `FixtureFetcher` replays those same URLs through the unchanged `backfill_source` pipeline (fetch → parse → diff → claims).
