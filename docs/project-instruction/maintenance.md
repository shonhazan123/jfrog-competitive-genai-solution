# Maintenance — purge stale pipeline data

Operators can wipe research findings while keeping the entity/source registry
and raw captures intact.

## `reset_findings`

**Module:** `app.services.maintenance`  
**CLI:** from `backend/`, run:

```bash
python -m app.services.maintenance
```

`reset_findings(session)` deletes every row produced by the research-engine pipeline:

- Vector chunks (`Chunk`)
- Signals and signal evidence (`Signal`, `SignalEvidence`)
- Claims, versions, and evidence (`Claim`, `ClaimVersion`, `Evidence`)

It does **not** delete:

- Registry rows (`Entity`, `Source`)
- Raw captures (fixture / fetch history tables)

Returns a `dict[str, int]` mapping each cleared table name to the number of rows
deleted. The CLI entrypoint commits after running.

Use before re-running per-surface agents on a clean slate after pipeline or schema changes.
