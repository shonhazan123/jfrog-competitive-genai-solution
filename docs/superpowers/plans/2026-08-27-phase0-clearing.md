# Phase 0 — Clearing the Old Pipeline: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the single `interpret` pipeline and the noisy RSS seeders so the branch is a clean slate for the three per-surface research agents — with the test suite green after every task and no irrelevant data left in the DB.

**Architecture:** Pure removal, ordered so the suite stays green at each step: first detach `interpret` from the run wiring, then delete the batch functions, then the service and graph, then the noise sources, then purge stale findings. No new features here — the pages will be intentionally empty until the agent plans land. Tables are reused, not dropped; the two column additions (`claim.stance`, `signal.theme_key`) belong to the agent plans, not this one.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, APScheduler.

**Spec:** [docs/superpowers/specs/2026-08-27-per-surface-research-graphs-design.md](../specs/2026-08-27-per-surface-research-graphs-design.md) — see §11 (Phase 0).

## Global Constraints

- Branch is `jfrog_agent_v2` — deletion is safe; **delete, don't disable** (history lives in git).
- **The full test suite must pass after every task.** Run `pytest -q` from the repo root (or `backend/`) before each commit.
- **Do not touch** in this plan (deferred to agent plans): `config/themes.yaml`, `app/services/industry_themes.py`, `tests/test_industry_themes.py`, the `llm.yaml` `extract`/`contextualize` roles and their config test, the `osv` adapter, `app/services/signals/clustering.py`, `app/services/scoring/materiality.py`.
- **Keep** these sources in `sources.yaml` (fate decided later, not now): `osv_nexus`, `cisa_advisories`, and all competitor product feeds (`sonatype_*`, `github_*`, `gitlab_blog`, `harbor_releases`, `azure_artifacts_news`, `sonatype_jobs`).
- Commit after each task with the message shown in its final step.

---

## File map

**Modified:** `backend/app/controllers/runs.py`, `backend/worker/scheduler.py`, `backend/worker/jobs.py`, `config/sources.yaml`, `tests/test_jobs.py`, `tests/test_api_writes.py`, `tests/test_config.py`
**Deleted:** `backend/app/services/agent_service.py`, `backend/agent/graphs/interpret/` (whole dir), `tests/test_agent_service.py`, `tests/test_interpret_graph.py`, and (grep-guarded) `backend/agent/schemas.py`, `backend/agent/prompts/extract.md`, `backend/agent/prompts/contextualize.md`, `backend/app/services/claim_lookup.py`, `backend/app/services/verification.py`
**Created:** `backend/app/services/maintenance.py`, `tests/test_maintenance.py`

---

### Task 1: Detach `interpret` from the run wiring

`run_interpret` still exists after this task (deleted in Task 2); we only stop the scheduler and the manual run from calling it, so the suite stays green.

**Files:**
- Modify: `backend/app/controllers/runs.py`
- Modify: `backend/worker/scheduler.py`

**Interfaces:**
- Produces: the `manual` run kind now runs `collect → score` only; `interpret` run kind removed.

- [ ] **Step 1: Remove the interpret entries from `runs.py`**

In `_JOB_BY_KIND`, delete the line:
```python
    "interpret": "run_interpret",
```
In `_RUN_STAGE_JOBS`, delete the whole `"interpret"` entry:
```python
    "interpret": [("extract", "run_interpret", {})],
```
In `_RUN_STAGE_JOBS["manual"]`, delete the extract stage and its comment so `manual` becomes:
```python
    "manual": [
        ("collect", "run_collection", {"force": True}),
        ("score", "run_scoring", {}),
    ],
```
Delete the `trigger_interpret` function entirely:
```python
def trigger_interpret() -> dict:
    global _last_run_at
    _last_run_at = datetime.now(UTC)
    return jobs.run_interpret()
```

- [ ] **Step 2: Remove the interpret job from the scheduler**

In `backend/worker/scheduler.py`, change the import to drop `run_interpret`:
```python
from worker.jobs import run_collection, run_scoring
```
and delete the line:
```python
    scheduler.add_job(run_interpret,  CronTrigger(hour=6, minute=15), id="interpret")
```

- [ ] **Step 3: Confirm nothing else references the removed symbols**

Run: `grep -rn "trigger_interpret\|run_interpret" backend --include=*.py`
Expected: matches only in `backend/worker/jobs.py` (the definition, removed in Task 2) and — via monkeypatch — `tests/test_api_writes.py` and `tests/test_jobs.py` (removed in Task 2). No other production references.

- [ ] **Step 4: Run the suite**

Run: `pytest -q`
Expected: PASS (green). `test_manual_run_invokes_the_same_job_the_scheduler_calls` still passes because it posts `kind: "collect"`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/controllers/runs.py backend/worker/scheduler.py
git commit -m "refactor: detach interpret from run wiring (Phase 0)"
```

---

### Task 2: Delete the interpret batch functions from `jobs.py`

**Files:**
- Modify: `backend/worker/jobs.py`
- Modify: `tests/test_jobs.py`
- Modify: `tests/test_api_writes.py`

**Interfaces:**
- Produces: `worker.jobs` no longer defines `run_interpret`, `_interpret_one`, `_diversify_by_source`, or `PER_SOURCE_INTERPRET_CAP`.

- [ ] **Step 1: Remove the interpret tests from `tests/test_jobs.py`**

Delete these six test functions (they exercise the code we're about to remove):
`test_run_interpret_continues_after_a_capture_failure`,
`test_run_interpret_counts_empty_captures`,
`test_run_interpret_dedups_identical_captures`,
`test_run_interpret_runs_captures_concurrently`,
`test_run_interpret_excludes_snapshot_captures`,
`test_run_interpret_caps_captures_per_source`.
Keep every `test_*collection*`, `test_two_domains_fetch_concurrently`, and `test_manual_window_skips_old_feed_entries`.

- [ ] **Step 2: Remove the `run_interpret` stub from the `spy_jobs` fixture in `tests/test_api_writes.py`**

Delete these lines from the `spy_jobs` fixture:
```python
    def stub_run_interpret(*args, **kwargs):
        spy.called = "run_interpret"
        return {}
```
and
```python
    monkeypatch.setattr(jobs, "run_interpret", stub_run_interpret)
```
(Leave the `run_collection` and `run_scoring` stubs.)

- [ ] **Step 3: Delete the functions and constant from `backend/worker/jobs.py`**

Remove the import:
```python
from app.services.agent_service import interpret_capture
```
Remove the constant:
```python
PER_SOURCE_INTERPRET_CAP = 3
```
Remove the functions `_diversify_by_source`, `_interpret_one`, and `run_interpret` in full. Then remove the now-unused imports at the top of the file: `from app.models.signal import Signal, SignalEvidence` becomes `from app.models.signal import Signal` only if `Signal` is still used by `run_scoring` (it is) — drop `SignalEvidence`.

- [ ] **Step 4: Verify no dangling references**

Run: `grep -rn "run_interpret\|_interpret_one\|_diversify_by_source\|PER_SOURCE_INTERPRET_CAP\|interpret_capture" backend/worker tests`
Expected: no matches.

- [ ] **Step 5: Run the suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/worker/jobs.py tests/test_jobs.py tests/test_api_writes.py
git commit -m "refactor: remove run_interpret batch and its tests (Phase 0)"
```

---

### Task 3: Delete `agent_service.py` and its orphaned helpers

**Files:**
- Delete: `backend/app/services/agent_service.py`, `tests/test_agent_service.py`
- Modify: `tests/test_api_writes.py`
- Delete (grep-guarded): `backend/agent/schemas.py`, `backend/agent/prompts/extract.md`, `backend/agent/prompts/contextualize.md`, `backend/app/services/claim_lookup.py`, `backend/app/services/verification.py`

- [ ] **Step 1: Remove the `_production_deps` test from `tests/test_api_writes.py`**

Delete the whole function:
```python
def test_extract_prompt_includes_instruction_when_present(client_with_data, session):
    from app.services.agent_service import _production_deps
    ...
    assert "flag anything mentioning SLSA" in prompt_text
```

- [ ] **Step 2: Delete the service and its test**

```bash
git rm backend/app/services/agent_service.py tests/test_agent_service.py
```

- [ ] **Step 3: Confirm nothing imports `agent_service`**

Run: `grep -rn "agent_service" backend tests --include=*.py`
Expected: no matches. (If any remain, they are dead imports — remove them.)

- [ ] **Step 4: Grep-guarded deletion of orphaned helpers**

For each helper, run its grep; if the only matches are the file itself (and a test that solely tests it), delete the file (and that test). Rule: **zero production references outside the module → delete.**

```bash
grep -rn "build_extraction_model\|Contextualisation" backend/agent backend/app tests --include=*.py
grep -rn "DbClaimLookup\|claim_lookup" backend/app backend/agent tests --include=*.py
grep -rn "verify_quote\|from app.services.verification" backend/app backend/agent tests --include=*.py
```
- `agent/schemas.py`: if `build_extraction_model`/`Contextualisation` have no remaining importer, `git rm backend/agent/schemas.py`. If `schemas.py` also holds symbols still used elsewhere, delete only those two definitions.
- `agent/prompts/extract.md`, `agent/prompts/contextualize.md`: `git rm` — they were loaded only by the interpret deps.
- `app/services/claim_lookup.py`: `git rm` if `DbClaimLookup` is unreferenced.
- `app/services/verification.py`: `git rm` (and any `tests/test_verification*.py`) only if `verify_quote` is unreferenced. **Note:** `config/verification.yaml` is config data, not an import — it does not count as a reference; leave it.

- [ ] **Step 5: Run the suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: delete agent_service and orphaned interpret helpers (Phase 0)"
```

---

### Task 4: Delete the interpret graph package

**Files:**
- Delete: `backend/agent/graphs/interpret/` (entire directory), `tests/test_interpret_graph.py`

- [ ] **Step 1: Confirm the graph has no importers left**

Run: `grep -rn "graphs.interpret\|build_interpret_graph" backend tests --include=*.py`
Expected: matches only inside `backend/agent/graphs/interpret/` and `tests/test_interpret_graph.py` (all about to be deleted).

- [ ] **Step 2: Delete the package and its test**

```bash
git rm -r backend/agent/graphs/interpret tests/test_interpret_graph.py
```

- [ ] **Step 3: Run the suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: delete interpret graph package (Phase 0)"
```

---

### Task 5: Remove the noise sources from `sources.yaml`

Removes the industry-entity RSS/HN/model-news seeders that produced the off-field radar noise. Keeps `cisa_advisories`, `osv_nexus`, and all competitor feeds (their fate is an agent-plan decision).

**Files:**
- Modify: `config/sources.yaml`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Delete the seven noise rows from `config/sources.yaml`**

Remove the complete YAML blocks for these keys: `hn_jfrog`, `hn_sonatype`, `thenewstack_rss`, `infoq_rss`, `gnews_funding`, `huggingface_blog`, `gnews_model_registry`. (Remove the surrounding section comments that only describe removed rows too.)

- [ ] **Step 2: Update `tests/test_config.py`**

In `test_source_registry_excludes_jfrog_and_includes_competitor_feeds`, change the `expected` set to drop the removed keys:
```python
    expected = {
        "github_changelog",
        "github_blog",
        "gitlab_blog",
        "azure_artifacts_news",
        "cisa_advisories",
    }
    assert expected <= keys
```
Delete the two assertions that reference `gnews_funding`:
```python
    assert by_key["gnews_funding"].reliability_grade == "C"
```
and
```python
    assert "corporate_financial" in by_key["gnews_funding"].covers
```
Keep the `github_changelog`, `github_blog`, `cisa_advisories`, and `gitlab_blog` assertions.

- [ ] **Step 3: Confirm the removed keys are gone**

Run: `grep -n "hn_jfrog\|hn_sonatype\|thenewstack_rss\|infoq_rss\|gnews_funding\|huggingface_blog\|gnews_model_registry" config/sources.yaml`
Expected: no matches.

- [ ] **Step 4: Run the suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/sources.yaml tests/test_config.py
git commit -m "chore: remove industry-noise RSS sources (Phase 0)"
```

---

### Task 6: Purge stale findings from the DB

Gives a clean slate: removes every row produced by the old pipeline (signals, claims, evidence, vector chunks, analyst queue) while keeping the registry (entities, sources) and raw captures.

**Files:**
- Create: `backend/app/services/maintenance.py`
- Test: `tests/test_maintenance.py`

**Interfaces:**
- Produces: `reset_findings(session) -> dict[str, int]` — deletes finding rows, returns per-table counts.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_maintenance.py
from datetime import UTC, datetime


def test_reset_findings_clears_signals_and_claims_but_keeps_registry(session):
    from app.models.registry import Entity, Source
    from app.models.signal import Signal
    from app.models.ledger import Claim
    from app.services.seeding import seed
    from app.services.maintenance import reset_findings

    seed(session)
    entity = session.query(Entity).filter_by(slug="sonatype").one()
    source = session.query(Source).filter_by(entity_id=entity.id).first()
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    session.add(Signal(
        source_id=source.id, entity_id=entity.id, signal_type="product_capability",
        headline="stale signal", occurred_at=datetime.now(UTC), cluster_key="k1",
    ))
    session.add(Claim(
        subject_entity_id=jfrog.id, asserting_entity_id=entity.id,
        claim_text="stale claim", claim_type="positioning", dimension="artifact_management",
        reliability_grade="C", first_seen_at=datetime.now(UTC),
    ))
    session.flush()

    entities_before = session.query(Entity).count()
    sources_before = session.query(Source).count()

    reset_findings(session)

    assert session.query(Signal).count() == 0
    assert session.query(Claim).count() == 0
    assert session.query(Entity).count() == entities_before
    assert session.query(Source).count() == sources_before
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `pytest tests/test_maintenance.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.maintenance`.

- [ ] **Step 3: Implement `reset_findings`**

```python
# backend/app/services/maintenance.py
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.delivery import Chunk
from app.models.ledger import Claim, ClaimVersion, Evidence
from app.models.signal import AnalystAction, AnalystQueue, Signal, SignalEvidence


def reset_findings(session: Session) -> dict[str, int]:
    """Delete every row produced by the interpret/agent pipeline, keeping the
    registry (entities, sources) and raw captures. Children before parents so
    foreign keys never block the delete."""
    counts: dict[str, int] = {}
    for model in (
        Chunk,            # vector index rows
        SignalEvidence,   # signal children
        Evidence,         # claim children
        ClaimVersion,     # claim children
        Signal,
        Claim,
        AnalystQueue,
        AnalystAction,
    ):
        counts[model.__tablename__] = session.query(model).delete()
    session.flush()
    return counts


if __name__ == "__main__":  # pragma: no cover - operational entrypoint
    from app.db.session import SessionLocal

    with SessionLocal() as s:
        report = reset_findings(s)
        s.commit()
        print("reset_findings:", report)
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `pytest tests/test_maintenance.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/maintenance.py tests/test_maintenance.py
git commit -m "feat: reset_findings to purge stale pipeline data (Phase 0)"
```

---

## Post-Phase-0 state (expected)

- Collection still runs (feeds/APIs/snapshots → `RawCapture`), but nothing consumes captures into `Signal`/`Claim` — the Signals, Industry, and Comparison pages are **intentionally empty** until the agent plans land.
- `interpret` is gone entirely; the `osv` adapter, Ask corpus, retrieval, scoring, and digest are untouched.
- The DB holds no stale findings; `claim.stance` / `signal.theme_key` are **not** added yet (agent plans).
- `themes.yaml` + `industry_themes.py` still present (replaced in the Industry agent plan).

## Self-Review

- **Spec coverage (§11):** bridge side-effect → deleted in Task 3 (it lived in `agent_service`); interpret orchestration → Tasks 1–2; interpret graph → Task 4; RSS seeders → Task 5; run wiring → Task 1; dead tests → Tasks 2–4; data purge (the "no irrelevant data" requirement) → Task 6. `themes.yaml` deferral is explicit per Global Constraints. OSV adapter retained per Global Constraints. ✓
- **Placeholder scan:** every step has concrete edits, grep commands, or code. Grep-guarded deletions (Task 3 Step 4) state the exact decision rule rather than "remove if needed." ✓
- **Type consistency:** `reset_findings(session) -> dict[str,int]` defined once and used by its test with matching import path. Model imports (`Chunk` from `app.models.delivery`; `Claim/ClaimVersion/Evidence` from `app.models.ledger`; `Signal/SignalEvidence/AnalystQueue/AnalystAction` from `app.models.signal`) match the codebase. ✓
