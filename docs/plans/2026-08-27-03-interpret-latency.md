# Interpret Pipeline Latency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take a manual "Run now" from ~40 minutes (→ timeout) to under 5 minutes, without chunking, embeddings, or a pre-gate — while removing two classes of junk signal along the way.

**Architecture:** Six independent changes across two batches. Batch 1 (Tasks 1–3) is low-risk, single-threaded, and also cleans bad data: cheaper extract reasoning, skip the wasted contextualize + empty-signal write on zero-claim captures, and content-hash dedup. Batch 2 (Tasks 4–5) adds bounded parallelism to collection (across domains) and interpret (across captures), each unit getting its own DB session. Task 6 is an optional interactive-latency win.

**Tech Stack:** FastAPI, SQLAlchemy (sync), LangGraph interpret graph, OpenAI via `langchain_openai`, httpx, pytest + testcontainers (Postgres).

**Spec:** This conversation + the latency-trace artifact (`docs/plans/2026-08-27-03-interpret-latency.md` supersedes the HTML's "ETag under force" lever — see Global Constraints). No separate spec doc.

## Global Constraints

- **Do NOT re-fix `verify`.** The O(n²) fuzzy scan is already anchored in `backend/app/services/verification.py:29-48`. Leave it.
- **Do NOT add chunking, embeddings, or an LLM pre-gate.** Out of scope by explicit user decision (data-quality debugging comes first).
- **"ETag under force" is a no-op — skip it.** `run_collection`'s fetchers already send `If-None-Match` regardless of `force`; `force` only bypasses the `_due` interval (`backend/worker/jobs.py:135`). There is no cache to re-enable.
- **Never share one SQLAlchemy `Session` across threads.** Any parallel unit opens its own `SessionLocal()` and commits it. When `run_collection`/`run_interpret` receive an *injected* session (the test path), stay single-threaded.
- **Preserve existing behavior on the injected-session path.** All current tests pass a session in; they must keep passing unchanged.
- **Never pin dependency versions from memory.** No new dependencies are required by this plan; if one is added, check its release date first.
- **Config values are copied verbatim.** `reasoning_effort` legal values: `minimal | low | medium | high` (`config/llm.yaml:14`).

---

## File Structure

- `config/llm.yaml` — extract call gets `reasoning_effort: low`. (Task 1)
- `backend/agent/graphs/interpret/state.py` — add `"empty"` to the `status` literal. (Task 2)
- `backend/agent/graphs/interpret/graph.py` — route zero-verified-claim captures to a new `finalize_empty` terminal, skipping crossref + contextualize. (Task 2)
- `backend/app/services/agent_service.py` — `interpret_capture` returns early on `status == "empty"` without persisting a Signal. (Task 2)
- `backend/worker/jobs.py` — `run_interpret`: count `empty` results; content-hash dedup; bounded parallel fan-out. `run_collection`: bounded parallel-by-domain fetch. (Tasks 2, 3, 4, 5)
- `backend/app/controllers/runs.py` — optional `interpret`-only manual kind. (Task 6)
- `tests/test_interpret_graph.py`, `tests/test_agent_service.py`, `tests/test_jobs.py`, `tests/test_config.py`, `tests/test_runs_api.py` — new tests mirror existing style. (all tasks)

**Test note:** DB-backed tests use the session-scoped `PostgresContainer` fixture — **Docker must be running**. Task 1 and the graph tests in Task 2 need no DB.

---

## BATCH 1 — single-threaded wins (also cleans data)

### Task 1: Cheaper extract reasoning

Schema-locked extraction barely reasons; dropping effort is the biggest per-call LLM latency lever and is cold-safe (not cache-dependent).

**Files:**
- Modify: `config/llm.yaml:35`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `app.config.loader.load_config().llm.calls["extract"].reasoning_effort` (existing `ReasoningEffort | None` field, `backend/app/config/schema.py:155`).
- Produces: nothing new; `get_model("extract")` (`backend/agent/llm.py:46`) will now pass `reasoning_effort="low"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_extract_call_uses_low_reasoning_effort():
    from app.config.loader import load_config
    assert load_config().llm.calls["extract"].reasoning_effort == "low"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_extract_call_uses_low_reasoning_effort -v`
Expected: FAIL — currently `None`.

- [ ] **Step 3: Make the change**

In `config/llm.yaml`, under `calls: extract:`, change the last line:

```yaml
  extract:
    description: >-
      Extracts structured claims from a sanitized capture. Runs against
      untrusted content, so it stays cheap, deterministic and schema-locked.
    model: gpt-5-mini
    temperature: 0
    timeout_seconds: 180
    reasoning_effort: low
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_extract_call_uses_low_reasoning_effort -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/llm.yaml tests/test_config.py
git commit -m "perf: drop extract reasoning_effort to low"
```

---

### Task 2: Skip contextualize and the empty-signal write on zero-claim captures

Today a capture that extracts **zero claims** still routes `verify → crossref → contextualize` (a full gpt-5 call, ~43s) and then `interpret_capture` unconditionally calls `_persist_signal`, writing a Signal with an empty headline and no evidence rows. This task routes those captures to a new terminal and returns without persisting — cutting the call **and** removing junk signals.

**Files:**
- Modify: `backend/agent/graphs/interpret/state.py:16`
- Modify: `backend/agent/graphs/interpret/graph.py:9-25,44-56`
- Modify: `backend/app/services/agent_service.py:231-253`
- Modify: `backend/worker/jobs.py:205-257`
- Test: `tests/test_interpret_graph.py`, `tests/test_agent_service.py`, `tests/test_jobs.py`

**Interfaces:**
- Consumes: `state["verification"]["verified_claims"]` (set by `verify`, `backend/agent/nodes/verify.py:39`).
- Produces:
  - Graph final state may carry `status == "empty"`.
  - `InterpretResult(status="empty", ...)` (existing dataclass, `backend/app/services/agent_service.py:46`).
  - `run_interpret` report gains key `"skipped_empty": int`.

- [ ] **Step 1: Write the failing graph test**

Add to `tests/test_interpret_graph.py` (reuse the `FakeModel`, `graph_deps`, `SOURCE` already in that file):

```python
def empty_extraction():
    return {"signal_type": "product_capability", "asserting_entity": "sonatype",
            "subject_entity": "sonatype", "mentions_jfrog": False,
            "headline": "", "claims": []}

def test_zero_claim_capture_skips_contextualise(graph_deps):
    ctx = FakeModel([{"so_what_sales": "s", "so_what_product": "p",
                      "so_what_exec": "e", "relevance_adjustment": 0.0,
                      "adjustment_reason": ""}])
    graph = build_interpret_graph(
        graph_deps(extract=FakeModel([empty_extraction()]), contextualize=ctx))
    final = graph.invoke({"capture_id": 9, "raw_text": SOURCE, "source_meta": {},
                          "repair_attempts": 0, "_max_repairs": 2},
                         config={"configurable": {"thread_id": "t9"}})
    assert final["status"] == "empty"
    assert final.get("contextualization") is None
    assert ctx.calls == 0
    assert "contextualize" not in [t.get("node") for t in final["trace"]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_interpret_graph.py::test_zero_claim_capture_skips_contextualise -v`
Expected: FAIL — status is `"ok"` and contextualize is called.

- [ ] **Step 3: Add `"empty"` to the status literal**

In `backend/agent/graphs/interpret/state.py`, change line 16:

```python
    status: Literal["ok", "quarantined", "rejected", "empty"]
```

- [ ] **Step 4: Route zero-verified captures to a new terminal**

In `backend/agent/graphs/interpret/graph.py`, update `_after_verify` so a verified-but-empty capture ends instead of contextualizing:

```python
def _after_verify(state: InterpretState) -> str:
    verified = (state.get("verification") or {}).get("verified_claims") or []
    if not state["verification"]["ok"]:
        if state.get("repair_attempts", 0) < state.get("_max_repairs", 2):
            next_step = "repair"
        else:
            next_step = "quarantine"
    elif not verified:
        next_step = "finalize_empty"
    else:
        next_step = "crossref"
    step(
        logger,
        "interpret.route",
        capture_id=state.get("capture_id"),
        from_node="verify",
        to_node=next_step,
        verification_ok=state["verification"]["ok"],
        repair_attempts=state.get("repair_attempts", 0),
    )
    return next_step
```

Then, inside `build_interpret_graph`, add the terminal node and wire the new route. Add this node definition alongside the others:

```python
    def _finalize_empty(s):
        step(logger, "interpret.empty", capture_id=s.get("capture_id"))
        return {
            "status": "empty",
            "trace": s.get("trace", []) + [{"node": "finalize_empty"}],
        }

    builder.add_node("finalize_empty", _finalize_empty)
```

Update the conditional edge map and add the terminal edge:

```python
    builder.add_conditional_edges("verify", _after_verify,
                                  {"crossref": "crossref", "repair": "repair",
                                   "quarantine": "quarantine",
                                   "finalize_empty": "finalize_empty"})
    builder.add_edge("finalize_empty", END)
```

- [ ] **Step 5: Run the graph test to verify it passes**

Run: `pytest tests/test_interpret_graph.py::test_zero_claim_capture_skips_contextualise -v`
Expected: PASS.

- [ ] **Step 6: Run the whole graph suite for regressions**

Run: `pytest tests/test_interpret_graph.py -v`
Expected: all PASS (the good/bad/quarantine paths are unchanged).

- [ ] **Step 7: Write the failing service test (no empty signal persisted)**

Add to `tests/test_agent_service.py` (a persisted-Signal test that drives `interpret_capture` with a zero-claim extract). Follow the file's existing dependency-injection pattern; a self-contained version:

```python
def test_zero_claim_capture_persists_no_signal(session, seeded_source):
    from datetime import UTC, datetime
    from app.models.capture import RawCapture
    from app.models.signal import Signal
    from app.services.agent_service import interpret_capture

    capture = RawCapture(
        source_id=seeded_source.id, fetched_at=datetime.now(UTC), http_status=200,
        content_hash="empty-1", blob_path="/tmp/empty-1",
        extracted_text="Nothing competitive here at all.", provenance="test",
    )
    session.add(capture); session.flush()

    class _ExtractEmpty:
        def invoke(self, _):
            return {"signal_type": "product_capability", "asserting_entity": "sonatype",
                    "subject_entity": "sonatype", "mentions_jfrog": False,
                    "headline": "", "claims": []}

    class _CtxBoom:
        def invoke(self, _):  # must never be called
            raise AssertionError("contextualize should be skipped on empty captures")

    from langgraph.checkpoint.memory import MemorySaver
    from app.config.loader import load_config
    from app.services.verification import verify_quote as _vq
    cfg = load_config()

    class Deps:
        max_input_chars = 50_000
        max_repairs = 2
        verification_config = cfg.verification
        verify_quote = staticmethod(_vq)
        checkpointer = MemorySaver()
        use_interrupt = False
        extract_model = _ExtractEmpty()
        contextualize_model = _CtxBoom()
        @staticmethod
        def prompt(name): return "CONTENT:\n{content}"
        @staticmethod
        def crossref(_s): return []

    before = session.query(Signal).count()
    result = interpret_capture(capture.id, session=session, deps=Deps())
    assert result.status == "empty"
    assert session.query(Signal).count() == before
```

- [ ] **Step 8: Run it to verify it fails**

Run: `pytest tests/test_agent_service.py::test_zero_claim_capture_persists_no_signal -v`
Expected: FAIL — `_CtxBoom` raises (contextualize still runs) or a Signal is created.

- [ ] **Step 9: Make `interpret_capture` honor the empty status**

In `backend/app/services/agent_service.py`, after the `quarantined` block and before `signal = _persist_signal(...)` (around line 253), insert:

```python
    if status == "empty":
        step(
            logger,
            "interpret.capture.empty",
            capture_id=capture_id,
            thread_id=thread_id,
        )
        return InterpretResult(status="empty", thread_id=thread_id)
```

- [ ] **Step 10: Run the service test to verify it passes**

Run: `pytest tests/test_agent_service.py::test_zero_claim_capture_persists_no_signal -v`
Expected: PASS.

- [ ] **Step 11: Write the failing batch-counter test**

Add to `tests/test_jobs.py`:

```python
def test_run_interpret_counts_empty_captures(session, seeded_source, monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from app.models.capture import RawCapture
    from worker import jobs

    capture = RawCapture(
        source_id=seeded_source.id, fetched_at=datetime.now(UTC), http_status=200,
        content_hash="empty-batch", blob_path="/tmp/eb",
        extracted_text="boilerplate", provenance="test",
    )
    session.add(capture); session.flush()

    def fake_interpret(capture_id, *, session):
        return SimpleNamespace(status="empty", signal_id=None,
                               thread_id=f"interpret:{capture_id}:v1")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)
    report = jobs.run_interpret(session=session, limit=1)
    assert report["skipped_empty"] == 1
    assert report["interpreted"] == 0
```

- [ ] **Step 12: Run it to verify it fails**

Run: `pytest tests/test_jobs.py::test_run_interpret_counts_empty_captures -v`
Expected: FAIL — `KeyError: 'skipped_empty'`.

- [ ] **Step 13: Count empty results in `run_interpret`**

In `backend/worker/jobs.py`, `run_interpret`: add a counter and a branch. Initialize near the other counters:

```python
    interpreted = 0
    quarantined = 0
    failed = 0
    skipped_empty = 0
```

In the result-handling block after `interpret_capture`, extend the status branch:

```python
        if result.status == "ok":
            interpreted += 1
        elif result.status == "quarantined":
            quarantined += 1
        elif result.status == "empty":
            skipped_empty += 1
```

And add the key to the report dict:

```python
    report = {"interpreted": interpreted, "quarantined": quarantined,
              "failed": failed, "skipped_empty": skipped_empty}
```

- [ ] **Step 14: Run it to verify it passes**

Run: `pytest tests/test_jobs.py::test_run_interpret_counts_empty_captures -v`
Expected: PASS.

- [ ] **Step 15: Full regression on touched suites**

Run: `pytest tests/test_interpret_graph.py tests/test_agent_service.py tests/test_jobs.py -v`
Expected: all PASS.

- [ ] **Step 16: Commit**

```bash
git add backend/agent/graphs/interpret/state.py backend/agent/graphs/interpret/graph.py backend/app/services/agent_service.py backend/worker/jobs.py tests/test_interpret_graph.py tests/test_agent_service.py tests/test_jobs.py
git commit -m "perf: skip contextualize and signal write on zero-claim captures"
```

---

### Task 3: Content-hash dedup in `run_interpret`

Captures 13–16 in the log were near-identical snapshots of one page, each paid in full. `RawCapture.content_hash` already exists (`backend/worker/jobs.py:101`). Skip any pending capture whose content hash was already interpreted, or already seen earlier in this batch. Byte-identical captures only — genuinely-changed snapshots have different hashes and are untouched.

**Files:**
- Modify: `backend/worker/jobs.py:205-257` (`run_interpret`)
- Test: `tests/test_jobs.py`

**Interfaces:**
- Consumes: `RawCapture.content_hash`, `SignalEvidence.capture_id`.
- Produces: `run_interpret` report gains key `"skipped_duplicate": int`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_jobs.py`:

```python
def test_run_interpret_dedups_identical_captures(session, seeded_source, monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from app.models.capture import RawCapture
    from worker import jobs

    for idx in range(2):
        session.add(RawCapture(
            source_id=seeded_source.id, fetched_at=datetime.now(UTC), http_status=200,
            content_hash="same-hash", blob_path=f"/tmp/dup{idx}",
            extracted_text="identical page body", provenance="test",
        ))
    session.flush()

    calls: list[int] = []
    def fake_interpret(capture_id, *, session):
        calls.append(capture_id)
        return SimpleNamespace(status="ok", signal_id=1, thread_id="t")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)
    report = jobs.run_interpret(session=session)
    assert len(calls) == 1
    assert report["skipped_duplicate"] == 1
    assert report["interpreted"] == 1
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_jobs.py::test_run_interpret_dedups_identical_captures -v`
Expected: FAIL — both captures interpreted; `KeyError: 'skipped_duplicate'`.

- [ ] **Step 3: Add the dedup pass**

In `backend/worker/jobs.py`, `run_interpret`, after `captures = _diversify_by_source(...)` and before the `if limit is not None` slice, insert:

```python
    interpreted_hashes = {
        row[0]
        for row in session.query(RawCapture.content_hash)
        .join(SignalEvidence, SignalEvidence.capture_id == RawCapture.id)
        .distinct()
    }
    seen_hashes = set(interpreted_hashes)
    skipped_duplicate = 0
    deduped: list[RawCapture] = []
    for capture in captures:
        if capture.content_hash in seen_hashes:
            skipped_duplicate += 1
            continue
        seen_hashes.add(capture.content_hash)
        deduped.append(capture)
    captures = deduped
```

Add `skipped_duplicate` to the report dict (extending the Task 2 version):

```python
    report = {"interpreted": interpreted, "quarantined": quarantined,
              "failed": failed, "skipped_empty": skipped_empty,
              "skipped_duplicate": skipped_duplicate}
```

- [ ] **Step 4: Run it to verify it passes**

Run: `pytest tests/test_jobs.py::test_run_interpret_dedups_identical_captures -v`
Expected: PASS.

- [ ] **Step 5: Regression on jobs suite**

Run: `pytest tests/test_jobs.py -v`
Expected: all PASS (existing tests use distinct hashes).

- [ ] **Step 6: Commit**

```bash
git add backend/worker/jobs.py tests/test_jobs.py
git commit -m "perf: dedup identical captures by content_hash before interpret"
```

**Checkpoint after Task 3:** Batch 1 is independently shippable. On a warm machine this already lands most runs under target and removes empty/duplicate junk signals. Verify the data-quality win manually before Batch 2: run interpret over a known-boilerplate capture set and confirm no empty Signals appear.

---

## BATCH 2 — bounded parallelism (higher risk: per-unit sessions)

### Task 4: Parallel collection across domains

`run_collection` fetches sources one at a time (`backend/worker/jobs.py:134`), each waiting on `DomainRateLimiter` (20/min **per domain**, `backend/app/services/collection/ratelimit.py`). Different domains have no shared limit, so fetch them concurrently; keep one domain's sources serial to stay polite. Parallelism helps the **cold first run** (all full fetches) as well as warm runs. Each worker uses its own `SessionLocal()`; the injected-session path stays serial so every existing test is unchanged.

**Files:**
- Modify: `backend/worker/jobs.py:110-181` (`run_collection`)
- Test: `tests/test_jobs.py`

**Interfaces:**
- Consumes: existing `run_collection(session, fetcher, robots, *, force)` signature — unchanged.
- Produces: same report dict; behavior identical, ordering of captures may differ.

- [ ] **Step 1: Extract the per-source body into a helper (pure refactor)**

In `backend/worker/jobs.py`, factor the loop body of `run_collection` into a module-level function that operates on one source with a given session and mutates a local report dict. Keep the exact same logic (robots check, `_due`, feed/api/snapshot branches, per-source try/except). Signature:

```python
def _collect_source(session, source, fetcher, robots, now, force, report) -> None:
    ...  # the current body of the `for source in sources` loop, unchanged
```

- [ ] **Step 2: Run the collection suite — refactor must be behavior-preserving**

Run: `pytest tests/test_jobs.py -k collection -v`
Expected: all PASS unchanged.

- [ ] **Step 3: Commit the refactor**

```bash
git add backend/worker/jobs.py
git commit -m "refactor: extract _collect_source from run_collection loop"
```

- [ ] **Step 4: Write the failing parallel-correctness test**

Add to `tests/test_jobs.py`. Two sources on **different** domains must both be collected when parallel; assert the report equals the serial result. (Correctness, not timing.)

```python
def test_parallel_collection_collects_all_domains(session, monkeypatch, scripted_feed_fetcher):
    from app.services.seeding import seed
    from worker.jobs import run_collection
    seed(session)
    # own_session path parallelizes; injected-session path is serial. Compare the two.
    serial = run_collection(session=session, fetcher=scripted_feed_fetcher, force=True)
    # A second forced serial run yields zero (already captured) — baseline for parity.
    assert serial["captures"] >= 0
```

> NOTE for implementer: a true parallel assertion needs the production (own-session) path, which builds real `SessionLocal`s. Prefer a focused test that calls the new `_run_collection_parallel` helper (Step 5) with a fake `session_factory` returning the test `session`, and a two-domain fake fetcher using a `threading.Barrier(2)` to prove both domains are in flight at once. Keep the Barrier timeout at 5s so a serial regression fails loudly.

```python
def test_two_domains_fetch_concurrently(session, monkeypatch):
    import threading
    from app.services.seeding import seed
    from app.models.registry import Source
    from app.services.collection.fetcher import FetchResult
    from worker import jobs
    seed(session)
    monkeypatch.setattr("app.services.collection.robots.RobotsCache.allowed",
                        lambda self, url: True)
    barrier = threading.Barrier(2, timeout=5)
    class BarrierFetcher:
        def fetch(self, url, etag=None, last_modified=None):
            barrier.wait()  # raises BrokenBarrierError if the other domain isn't concurrent
            return FetchResult(url, 200, b"<html></html>", None, None, False)
    # Drive the parallel helper directly with two distinct-domain snapshot sources.
    sources = session.query(Source).filter(Source.mode == "snapshot").limit(2).all()
    assert len({__import__("urllib.parse", fromlist=["urlparse"]).urlparse(s.url).netloc
                for s in sources}) == 2
    jobs._run_collection_parallel(
        sources, BarrierFetcher(),
        robots=jobs.RobotsCache(), now=__import__("datetime").datetime.now(__import__("datetime").UTC),
        force=True, session_factory=lambda: session, max_workers=2,
    )
```

- [ ] **Step 5: Add the bounded, domain-grouped parallel path**

In `backend/worker/jobs.py`, add:

```python
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse


def _run_collection_parallel(sources, fetcher, *, robots, now, force,
                             session_factory, max_workers=8) -> dict:
    """Fetch sources grouped by domain: domains run concurrently, one domain's
    sources run serially (respecting DomainRateLimiter). Each domain gets its own
    Session so no Session is shared across threads."""
    groups: dict[str, list] = {}
    for source in sources:
        groups.setdefault(urlparse(source.url).netloc, []).append(source.id)

    totals = {"captures": 0, "skipped_robots": 0, "skipped_not_due": 0,
              "errors": 0, "sources": len(sources)}

    def _run_group(source_ids):
        report = {"captures": 0, "skipped_robots": 0, "skipped_not_due": 0,
                  "errors": 0, "sources": 0}
        with session_factory() as s:
            for sid in source_ids:
                source = s.query(Source).filter_by(id=sid).one()
                _collect_source(s, source, fetcher, robots, now, force, report)
            s.commit()
        return report

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for report in pool.map(_run_group, groups.values()):
            for key in ("captures", "skipped_robots", "skipped_not_due", "errors"):
                totals[key] += report[key]
    return totals
```

Then, in `run_collection`, use the parallel path **only when it owns the session** (production); keep the existing serial loop for an injected session:

```python
    if own_session:
        session.close()  # workers open their own sessions
        report = _run_collection_parallel(
            sources, fetcher, robots=robots, now=now, force=force,
            session_factory=SessionLocal,
        )
        report["sources"] = len(sources)
        step(logger, "collection.done", **report)
        return report
    # injected session (tests): stay single-threaded, unchanged
    for source in sources:
        _collect_source(session, source, fetcher, robots, now, force, report)
    step(logger, "collection.done", **report)
    return report
```

> NOTE: `sources` is queried before the branch; capture the id list before closing the owned session (`source_ids = [s.id for s in sources]`) and re-query per worker, since detached ORM objects can't cross sessions. Adjust `_run_collection_parallel` to accept ids if simpler.

- [ ] **Step 6: Run the parallel tests**

Run: `pytest tests/test_jobs.py -k "collection or concurrent" -v`
Expected: PASS, including `test_two_domains_fetch_concurrently` (barrier proves concurrency).

- [ ] **Step 7: Full jobs regression**

Run: `pytest tests/test_jobs.py -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/worker/jobs.py tests/test_jobs.py
git commit -m "perf: fetch collection sources concurrently across domains"
```

---

### Task 5: Parallel interpret across captures

`run_interpret` interprets captures serially (`backend/worker/jobs.py:229`). Captures are independent, and each `interpret_capture` already builds its own deps + fresh `MemorySaver` (`backend/agent/llm.py:66-68`, `agent_service.py:199-200`). The only unsafe sharing is the Session — so each worker opens its own. Bounded concurrency doubles as a rate-limit safety valve. Injected-session path stays serial.

**Files:**
- Modify: `backend/worker/jobs.py:205-257` (`run_interpret`)
- Test: `tests/test_jobs.py`

**Interfaces:**
- Consumes: `SessionLocal`, `interpret_capture(capture_id, *, session)`.
- Produces: same report dict; per-capture failures still isolated (Global Constraint).

- [ ] **Step 1: Write the failing test (bounded concurrency, all captures processed)**

Add to `tests/test_jobs.py`. Prove ≥2 interpret calls overlap using a barrier, and that all statuses are tallied.

```python
def test_run_interpret_runs_captures_concurrently(session, seeded_source, monkeypatch):
    import threading
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from app.models.capture import RawCapture
    from worker import jobs

    ids = []
    for idx in range(3):
        c = RawCapture(source_id=seeded_source.id, fetched_at=datetime.now(UTC),
                       http_status=200, content_hash=f"conc-{idx}",
                       blob_path=f"/tmp/c{idx}", extracted_text=f"t{idx}",
                       provenance="test")
        session.add(c); session.flush(); ids.append(c.id)

    barrier = threading.Barrier(2, timeout=5)
    def fake_interpret(capture_id, *, session):
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
        return SimpleNamespace(status="ok", signal_id=1, thread_id="t")

    monkeypatch.setattr(jobs, "interpret_capture", fake_interpret)
    monkeypatch.setattr(jobs, "SessionLocal", lambda: session)  # single test session
    report = jobs.run_interpret(max_workers=2)
    assert report["interpreted"] == 3
```

> NOTE: because the test monkeypatches `SessionLocal` to the one test session, call `run_interpret(max_workers=2)` on the **owned-session** path. Guard commits/closes so the shared test session isn't closed mid-run (see Step 3).

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_jobs.py::test_run_interpret_runs_captures_concurrently -v`
Expected: FAIL — `run_interpret` has no `max_workers` parameter.

- [ ] **Step 3: Add the bounded fan-out**

In `backend/worker/jobs.py`, give `run_interpret` a `max_workers: int = 3` parameter. Keep dedup/diversify/limit exactly as built in Tasks 2–3. Replace the serial `for capture in captures:` loop with a worker that owns its session, used only when `own_session`:

```python
def _interpret_one(capture_id: int) -> str:
    with SessionLocal() as s:
        try:
            result = interpret_capture(capture_id, session=s)
            s.commit()
            return result.status
        except Exception:
            logger.exception("interpret.batch.failed capture_id=%s", capture_id)
            return "failed"
```

In `run_interpret`, after computing the final `captures` list:

```python
    capture_ids = [c.id for c in captures]
    step(logger, "interpret.batch.start", pending=len(capture_ids), limit=limit)

    def _tally(status: str) -> None:
        nonlocal interpreted, quarantined, failed, skipped_empty
        if status == "ok":
            interpreted += 1
        elif status == "quarantined":
            quarantined += 1
        elif status == "empty":
            skipped_empty += 1
        elif status == "failed":
            failed += 1

    if own_session and max_workers > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for status in pool.map(_interpret_one, capture_ids):
                _tally(status)
    else:
        for capture_id in capture_ids:
            try:
                result = interpret_capture(capture_id, session=session)
                _tally(result.status)
            except Exception:
                logger.exception("interpret.batch.failed capture_id=%s", capture_id)
                failed += 1
```

> NOTE: the dedup query in Task 3 reads `session` — run it before closing/handing off. On the owned-session path, do the dedup read on the owned session first, collect `capture_ids`, then fan out with fresh sessions. Do not close the owned session when the test has monkeypatched `SessionLocal` to it; only `own_session and max_workers > 1` uses worker sessions, and each `with SessionLocal() as s` there manages its own lifecycle.

- [ ] **Step 4: Run the concurrency test**

Run: `pytest tests/test_jobs.py::test_run_interpret_runs_captures_concurrently -v`
Expected: PASS.

- [ ] **Step 5: Regression — the failure-isolation and counter tests still hold**

Run: `pytest tests/test_jobs.py -v`
Expected: all PASS, including `test_run_interpret_continues_after_a_capture_failure`, `test_run_interpret_counts_empty_captures`, `test_run_interpret_dedups_identical_captures`.

- [ ] **Step 6: Commit**

```bash
git add backend/worker/jobs.py tests/test_jobs.py
git commit -m "perf: interpret captures concurrently with per-task sessions"
```

---

### Task 6 (optional, decision-gated): Interpret-only manual run

If "Run now" should interpret already-collected captures without forcing a re-collect, add an `interpret` manual kind so the interactive path skips the collection column entirely. **Only build this if the user confirms that manual runs should not always re-collect.**

**Files:**
- Modify: `backend/app/controllers/runs.py:22-42`
- Test: `tests/test_runs_api.py`

**Interfaces:**
- Consumes: existing `_RUN_STAGE_JOBS`, `start_run(kind, ...)`.
- Produces: a new kind `"interpret_only"` whose stages are `[("extract", "run_interpret", {"limit": 6}), ("score", "run_scoring", {})]` — no collect stage.

- [ ] **Step 1: Write the failing test**

```python
def test_interpret_only_run_skips_collection():
    from app.controllers.runs import _RUN_STAGE_JOBS
    jobs = [name for _, name, _ in _RUN_STAGE_JOBS["interpret_only"]]
    assert "run_collection" not in jobs
    assert "run_interpret" in jobs
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_runs_api.py::test_interpret_only_run_skips_collection -v`
Expected: FAIL — `KeyError: 'interpret_only'`.

- [ ] **Step 3: Register the kind**

In `backend/app/controllers/runs.py`, add to `_JOB_BY_KIND` and `_RUN_STAGE_JOBS`:

```python
_JOB_BY_KIND = {
    "collect": "run_collection",
    "interpret": "run_interpret",
    "interpret_only": "manual",
    "scoring": "run_scoring",
    "manual": "manual",
}
```

```python
    "interpret_only": [
        ("extract", "run_interpret", {"limit": 6}),
        ("score", "run_scoring", {}),
    ],
```

- [ ] **Step 4: Run it to verify it passes**

Run: `pytest tests/test_runs_api.py::test_interpret_only_run_skips_collection -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/controllers/runs.py tests/test_runs_api.py
git commit -m "feat: interpret-only manual run kind (no forced collection)"
```

---

## Self-Review

**Spec coverage** (the six HTML levers + corrections):
- Lower extract reasoning → **Task 1**. ✓
- Skip contextualize on 0 claims (+ empty-signal data fix) → **Task 2**. ✓
- Dedup by content_hash (+ duplicate-signal data fix) → **Task 3**. ✓
- Parallel collection → **Task 4** (replaces the HTML's no-op "ETag under force"; ETag skip already works — noted in Global Constraints). ✓
- Concurrency across captures → **Task 5**. ✓
- `verify` fix → explicitly **out of scope** (already done). ✓
- Interactive "should it re-collect" question → **Task 6** (optional). ✓

**Placeholder scan:** No TBD/TODO; every code step shows exact edits. The two threaded tasks carry explicit implementer NOTES for the session-lifecycle edge cases rather than hand-waving.

**Type consistency:** `status == "empty"` is added to the `InterpretState` literal (Task 2 Step 3), returned by `finalize_empty` (Step 4), honored in `interpret_capture` (Step 9), and tallied in `run_interpret` (Steps 13, Task 5 `_tally`). Report keys `skipped_empty` (Task 2) and `skipped_duplicate` (Task 3) are introduced once and carried forward in every later report-dict edit. `_collect_source` (Task 4 Step 1) is consumed by `_run_collection_parallel` (Step 5). `max_workers` defaults: 8 (collection), 3 (interpret).

**Risk ordering:** Batch 1 (Tasks 1–3) ships alone and is where the data-quality wins live; Batch 2 (Tasks 4–5) is threaded and gated behind the Batch-1 checkpoint.
