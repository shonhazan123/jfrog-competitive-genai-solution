# Run-Now Status Card + Today Running Bar: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. Follow the model + test conventions in `2026-08-27-00-EXECUTION.md` (Composer 2.5 for coding, Opus 4.8 for review; write tests per task, run the suite at plan end).

**Goal:** When `Run now` on Today fires all three investigators, show a live status card whose steps are in plain, non-technical language; let the user minimize it to a running bar on Today and reopen it; and handle the "found nothing" and "hit trouble" outcomes gracefully.

**Architecture:** The backend already fans out into three runs (`start_all`). This plan (1) makes each surface report a **human-readable step** + optional **detail counter** into its run, (2) groups the three runs into a recoverable **batch** so the bar survives navigation/reload, and (3) builds the frontend: a run store that polls the batch, the status card, and the docked bar. The plain-language step text is authored once on the backend (`config/surface_steps.yaml`) and simply displayed by the client — one source of truth.

**Tech Stack:** FastAPI, SQLAlchemy (in-memory run store), pytest; React + TypeScript, vitest.

**Visual reference (the design is settled):** the interactive sketch — three lanes, minimize-to-bar, empty/trouble states, "Show what the system is doing" toggle: https://claude.ai/code/artifact/ae4fcf05-e9d3-4fb0-80c6-72536a9bb313

## Global Constraints

- **Plain language only** in every user-facing string. Never surface "embedding", "chunking", "gate", "vector", "index" to the user. The one exception is behind the opt-in "Show what the system is doing" toggle.
- **Non-blocking:** the run keeps going if the card is minimized or the user navigates away. State must survive a route change and a page reload.
- **One global run at a time** (Run now disables while a batch is active). Per-page "Run this page" buttons are out of scope here.
- **Four lane states:** running, done (new items), empty (done, 0 items — calm, not an error), trouble (failed — amber, never a stack trace).
- **Bottom-centre** dock bar; theme-aware (light + dark); honor `prefers-reduced-motion`.
- Backend is the single source of truth for step text; the client displays `step_label`/`step_detail` verbatim.

## Step-label mapping (authored on the backend)

| phase | Market Watch (industry) | Competitor Moves (signals) | Head-to-Head (comparison) |
|-------|-------------------------|----------------------------|---------------------------|
| plan | Deciding what to look into | Lining up each competitor | Setting up the comparison grid |
| research | Searching the web for the latest | Checking hiring, pricing & funding | Researching each rival's strengths *(N of M)* |
| writing | Writing why each item matters | Writing the takeaways | Rating them against JFrog |
| saving | Making it searchable in Ask | Saving it for later | Filling in the grid |

---

## File map

**Backend — modified:** `backend/app/models/run.py` (Run fields + progress_body), `backend/app/controllers/runs.py` (reporter, batch, `active_batch`), `backend/app/routers/runs.py` (`GET /runs/active`), `backend/agent/graphs/research/skeleton.py` (progress hook), `backend/app/services/research/{industry,signals,comparison}_agent.py` (thread progress). **Created:** `config/surface_steps.yaml`.
**Frontend — created:** `client/src/state/runStore.tsx`, `client/src/components/RunStatusCard.tsx` (+`.css`), `client/src/components/TodayRunBar.tsx` (+`.css`), `client/src/utils/runPresentation.ts`. **Modified:** `client/src/api/client.ts`, `client/src/pages/Today.tsx`, `client/src/App.tsx` (mount the store provider + bar).

---

### Task 1: Run model carries a human step + detail + batch identity

**Files:** Modify `backend/app/models/run.py`. Test: `tests/test_run_progress.py`.

**Interfaces:**
- Produces: `Run` gains `step_label: str=""`, `step_detail: str|None=None`, `surface: str|None=None`, `batch_id: str|None=None`. `progress_body` includes `step_label`, `step_detail`, `surface`, `new_items`, `status`.

- [ ] **Step 1: Failing test**

```python
# tests/test_run_progress.py
def test_progress_body_exposes_human_step_and_detail():
    from app.models.run import create_run, update_run, progress_body, get_run
    run = create_run()
    update_run(run.id, surface="comparison", step_label="Researching each rival's strengths",
               step_detail="12 of 30", current=12, total=30)
    body = progress_body(get_run(run.id))
    assert body["surface"] == "comparison"
    assert body["step_label"] == "Researching each rival's strengths"
    assert body["step_detail"] == "12 of 30"
    assert body["progress"] == {"current": 12, "total": 30}
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Add the fields + expose them**

In the `Run` dataclass add (after `new_items`):
```python
    step_label: str = ""
    step_detail: str | None = None
    surface: str | None = None
    batch_id: str | None = None
```
In `progress_body` add to the returned dict:
```python
        "surface": run.surface,
        "step_label": run.step_label,
        "step_detail": run.step_detail,
```

- [ ] **Step 4: Run → PASS. Commit** `feat: run model carries human step + batch identity`.

---

### Task 2: The step labels config + a progress reporter

**Files:** Create `config/surface_steps.yaml`. Modify `backend/app/controllers/runs.py`. Test: `tests/test_surface_progress.py`.

**Interfaces:**
- Produces: `make_reporter(run_id, surface) -> Callable[[str, int|None, int|None], None]` — looks up the human label for `(surface, step_key)` from `surface_steps.yaml` and writes `step_label`/`step_detail`/`current`/`total` onto the run. `step_detail` is `"{current} of {total}"` only when both are given.

- [ ] **Step 1: Failing test**

```python
# tests/test_surface_progress.py
def test_reporter_writes_human_label_and_counter():
    from app.models.run import create_run, get_run
    from app.controllers.runs import make_reporter
    run = create_run()
    report = make_reporter(run.id, "comparison")
    report("research", current=12, total=30)
    r = get_run(run.id)
    assert r.step_label == "Researching each rival's strengths"
    assert r.step_detail == "12 of 30"
    assert r.current == 12 and r.total == 30

def test_reporter_without_counter_has_no_detail():
    from app.models.run import create_run, get_run
    from app.controllers.runs import make_reporter
    run = create_run()
    make_reporter(run.id, "industry")("plan")
    assert get_run(run.id).step_label == "Deciding what to look into"
    assert get_run(run.id).step_detail is None
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Write `config/surface_steps.yaml`** (the full mapping table above):

```yaml
industry:
  plan: "Deciding what to look into"
  research: "Searching the web for the latest"
  writing: "Writing why each item matters"
  saving: "Making it searchable in Ask"
signals:
  plan: "Lining up each competitor"
  research: "Checking hiring, pricing & funding"
  writing: "Writing the takeaways"
  saving: "Saving it for later"
comparison:
  plan: "Setting up the comparison grid"
  research: "Researching each rival's strengths"
  writing: "Rating them against JFrog"
  saving: "Filling in the grid"
```

- [ ] **Step 4: Implement `make_reporter` in `runs.py`**

```python
from functools import lru_cache
from pathlib import Path
import yaml
from app.settings import settings
from app.models.run import update_run

@lru_cache(maxsize=1)
def _surface_steps() -> dict:
    return yaml.safe_load(
        (Path(settings.config_dir) / "surface_steps.yaml").read_text(encoding="utf-8")
    )

def make_reporter(run_id: str, surface: str):
    labels = _surface_steps().get(surface, {})
    def report(step_key: str, current: int | None = None, total: int | None = None) -> None:
        fields = {"step_label": labels.get(step_key, step_key)}
        if current is not None and total is not None:
            fields["step_detail"] = f"{current} of {total}"
            fields["current"] = current
            fields["total"] = total
        else:
            fields["step_detail"] = None
        update_run(run_id, **fields)
    return report
```

- [ ] **Step 5: Run → PASS. Commit** `feat: surface_steps config + progress reporter`.

---

### Task 3: Thread progress through the research skeleton and agents

**Files:** Modify `backend/agent/graphs/research/skeleton.py`, the three `*_agent.py`, and `_run_surface` in `runs.py`. Test: `tests/test_skeleton_progress.py`.

**Interfaces:**
- `run_research(deps, progress=None)` — `progress(step_key, current, total)` is called `("plan", 0, N)` once, then `("research", i, N)` as each target resolves. Backward compatible (defaults to a no-op).
- `run_industry(progress=None)` / `run_signals(progress=None)` / `run_comparison(progress=None)` — pass `progress` to `run_research`, then call `progress("writing")` before synthesis/persist and `progress("saving")` before indexing.
- `_run_surface(run_id, kind)` builds `make_reporter(run_id, kind)` and passes it as `progress`.

- [ ] **Step 1: Failing test (skeleton reports plan + per-target research)**

```python
# tests/test_skeleton_progress.py
from agent.graphs.research.skeleton import run_research

class Deps:  # minimal: 3 targets, all resolve immediately
    max_attempts = 3
    def plan(self): return [{"id":1},{"id":2},{"id":3}]
    def collect(self, t): return {"ok": True}
    def search(self, t): return {"ok": True}
    def assess(self, t, m, a): return "resolved", {"id": t["id"]}
    def absent_draft(self, t): return {"id": t["id"], "absent": True}

def test_run_research_reports_plan_then_each_target():
    calls = []
    run_research(Deps(), progress=lambda step, current=None, total=None: calls.append((step, current, total)))
    assert calls[0] == ("plan", 0, 3)
    assert ("research", 1, 3) in calls and ("research", 3, 3) in calls
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Add the `progress` param to `run_research` and the skeleton**

In `skeleton.py`, give `build_research_graph`/`run_research` an optional `progress` (default `lambda *a, **k: None`). In `plan_node` call `progress("plan", 0, len(targets))`. In `resolve_node`, after incrementing the cursor, call `progress("research", state["cursor"] + 1, len(state["targets"]))`. Thread `progress` from `run_research(deps, progress=None)` into the node closures.

- [ ] **Step 4: Thread through the three agents + `_run_surface`**

Each `run_*` gains `progress=None`, passes it to `run_research`, and calls `progress("writing")` before persistence and `progress("saving")` before/around `index_finding`. In `runs.py` `_run_surface`, replace the coarse stage bumps with:
```python
    from app.controllers.runs import make_reporter  # or module-local
    reporter = make_reporter(run_id, kind)
    report = getattr(jobs, _SURFACE_JOBS[kind])(progress=reporter)
```
Keep the final `update_run(..., status="done", new_items=..., finished_at=...)`.

- [ ] **Step 5: Run → PASS. Full suite. Commit** `feat: granular human progress through agents`.

---

### Task 4: Batch grouping + `GET /runs/active` (reload recovery)

**Files:** Modify `backend/app/controllers/runs.py` (`start_all` tags batch; add `active_batch()`), `backend/app/routers/runs.py` (`GET /runs/active`). Test: `tests/test_run_batch.py`.

**Interfaces:**
- `start_all` sets `surface` and a shared `batch_id` on each run; returns `{"batch_id": bid, "run_ids": {...}}`.
- `active_batch() -> dict | None` — the newest batch with at least one un-finished run, as `{"batch_id", "runs": [progress_body(r) for r in batch]}`; `None` if none active.
- `GET /runs/active` → `active_batch()` or `204`/empty.

- [ ] **Step 1: Failing test**

```python
# tests/test_run_batch.py
def test_start_all_tags_a_batch_and_active_batch_recovers_it(monkeypatch):
    import app.controllers.runs as runs
    monkeypatch.setattr(runs, "_run_surface", lambda run_id, kind: None)  # don't actually run
    body = runs.start_all()
    assert "batch_id" in body and set(body["run_ids"]) == {"industry","signals","comparison"}
    active = runs.active_batch()
    assert active["batch_id"] == body["batch_id"]
    assert {r["surface"] for r in active["runs"]} == {"industry","signals","comparison"}
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement batch tagging + recovery**

In `start_all`, create `batch_id = uuid.uuid4().hex[:8]`; for each surface set `update_run(run.id, surface=kind, batch_id=batch_id)` after `create_run()`; return `{"batch_id": batch_id, "run_ids": run_ids}`. Add:
```python
def active_batch() -> dict | None:
    from app.models.run import _store, progress_body
    batches: dict[str, list] = {}
    for run in _store.values():
        if run.batch_id:
            batches.setdefault(run.batch_id, []).append(run)
    # newest batch first
    for bid, runs_ in sorted(batches.items(), key=lambda kv: max(r.started_at for r in kv[1]), reverse=True):
        if any(r.status == "running" for r in runs_):
            return {"batch_id": bid, "runs": [progress_body(r) for r in runs_]}
    return None
```

- [ ] **Step 4: Add the route** in `routers/runs.py` (place **above** the `/{run_id}` route so "active" isn't captured as an id):
```python
@router.get("/active")
def active() -> dict:
    return runs.active_batch() or {"batch_id": None, "runs": []}
```

- [ ] **Step 5: Run → PASS. Full suite. Commit** `feat: batch grouping + /runs/active recovery`.

---

### Task 5: Frontend run store

**Files:** Create `client/src/state/runStore.tsx`, `client/src/utils/runPresentation.ts`. Modify `client/src/api/client.ts`. Test: `client/src/state/runStore.test.tsx`.

**Interfaces:**
- `client.ts`: `startAllRuns() -> Promise<{batch_id, run_ids}>`; `getRunProgress(id) -> Promise<SurfaceProgress>`; `getActiveBatch() -> Promise<{batch_id, runs: SurfaceProgress[]}>`.
- `runPresentation.ts`: `SURFACE_META = { industry:{name:"Market Watch",…}, signals:{name:"Competitor Moves",…}, comparison:{name:"Head-to-Head",…} }`; `laneState(p) -> "running"|"done"|"empty"|"trouble"` (trouble = `status==="failed"`; empty = `status==="done" && new_items===0`; done = `status==="done" && new_items>0`; else running); `etaSeconds(surfaces) -> number` (per-surface expected seconds × remaining fraction, take the max).
- `runStore.tsx`: a React context exposing `{ active, surfaces, cardOpen, minimized, startAll(), openCard(), minimize() }`. `startAll` POSTs `/runs/all`, stores run_ids (+localStorage), opens the card, and begins a ~1500ms poll of each id until all resolve. On mount it calls `getActiveBatch()` to recover an in-flight batch (survives reload/route change). Polling stops when every surface is resolved.

- [ ] **Step 1: Failing test — lane-state derivation + recovery**

```tsx
// client/src/state/runStore.test.tsx
import { laneState, etaSeconds } from "../utils/runPresentation";

test("lane state derivation", () => {
  expect(laneState({ status: "running", new_items: 0 } as any)).toBe("running");
  expect(laneState({ status: "done", new_items: 5 } as any)).toBe("done");
  expect(laneState({ status: "done", new_items: 0 } as any)).toBe("empty");
  expect(laneState({ status: "failed", new_items: 0 } as any)).toBe("trouble");
});
```
(Add a store test that mounts the provider, mocks `getActiveBatch` to return one running batch, and asserts `active === true` with three surfaces — mirror the existing page-test setup for context/mocking in this repo.)

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement** `runPresentation.ts` (the pure functions above — test them first), then `client.ts` calls, then `runStore.tsx` (provider + poll loop + recovery). Persist `run_ids` to `localStorage` and clear them when the batch resolves. Poll with `setInterval`; guard against overlapping fetches.

- [ ] **Step 4: Run → PASS. Commit** `feat(client): run store with batch polling + recovery`.

---

### Task 6: The status card

**Files:** Create `client/src/components/RunStatusCard.tsx` (+`.css`). Test: `client/src/components/RunStatusCard.test.tsx`.

- [ ] **Step 1: Failing test** — render the card with a store value of three surfaces (one running with `step_detail:"12 of 30"`, one `done`, one `failed`); assert it shows the plain `step_label`, the "12 of 30" detail, the green "Open Head-to-Head →" for the done lane, and the amber "Had trouble" for the failed lane. Assert **no** technical strings ("embedding"/"index"/"gate") appear in the DOM unless the tech toggle is on.

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement** the card per the sketch: header (title, minimize `–`, shrinking ETA from `etaSeconds`, overall bar), three lanes each rendering `SURFACE_META.name`, `step_label`, `step_detail`, a progress bar from `progress.current/total`, and the four visual states; the "Show what the system is doing" toggle reveals a small `step_key` tag. Minimize calls `store.minimize()`.

- [ ] **Step 4: Run → PASS. Commit** `feat(client): run status card`.

---

### Task 7: The Today running bar

**Files:** Create `client/src/components/TodayRunBar.tsx` (+`.css`). Test: `client/src/components/TodayRunBar.test.tsx`.

- [ ] **Step 1: Failing test** — bar renders only when `active && minimized`; shows "N of 3 ready" + the ETA; clicking it calls `store.openCard()`; when all resolved it shows "All caught up · See what's new →" (and "N had trouble" when any surface is `trouble`).

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement** the docked bar (bottom-centre, fixed) reading the store; count `ready = surfaces.filter(resolved)`. Click → `openCard()`.

- [ ] **Step 4: Run → PASS. Commit** `feat(client): Today running bar`.

---

### Task 8: Wire it into Today + the app shell

**Files:** Modify `client/src/App.tsx` (wrap in `RunProvider`, mount `<RunStatusCard/>` + `<TodayRunBar/>` at the shell level so they persist across routes), `client/src/pages/Today.tsx` (Run now → `store.startAll()`, disable while `active`). Test: update `client/src/pages/today.test.tsx`.

- [ ] **Step 1: Update the Today test** — clicking `Run now` calls `startAllRuns` (mock the client) and disables the button while a batch is active.

- [ ] **Step 2: Implement** — mount the provider and the two components in `App.tsx` (not inside Today, so the bar survives navigation); point Today's `Run now` at `store.startAll`.

- [ ] **Step 3: Run `npm test` → PASS. Commit** `feat(client): wire Run now to the status card + persistent bar`.

---

## Self-Review

- **Design coverage:** plain-language steps (backend `surface_steps.yaml`, Task 2) → shown verbatim (Tasks 6–7); parallel lanes with per-surface progress + counter (Tasks 3, 6); minimize→bar→reopen (Tasks 6–8); survives navigation/reload (shell-mounted provider + `/runs/active`, Tasks 4–5, 8); empty/trouble states (`laneState`, Task 5; rendered Tasks 6–7); ETA (`etaSeconds`, Task 5); tech toggle (Task 6). ✓
- **Placeholder scan:** backend code is complete; frontend pure functions have full code/tests; component tasks specify exact assertions and the sketch is the visual spec. Store/component internals that mirror existing repo patterns are described with their required props + tests rather than pre-written line-for-line — acceptable where the repo's own component conventions govern. ✓
- **Type consistency:** `progress(step_key, current, total)` is identical across skeleton, agents, and `make_reporter`; `progress_body` fields (`surface`, `step_label`, `step_detail`) added in Task 1 are consumed by `active_batch` (Task 4) and the client `SurfaceProgress` (Task 5); `laneState` inputs match `progress_body`'s `status`/`new_items`. ✓
- **Ordering:** route `/runs/active` is added above `/{run_id}` (Task 4 Step 4) so it isn't swallowed by the path param. ✓
```
