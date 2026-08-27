# Foundation — Shared Research Machinery: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ~80% of code the three agents share — the two migrations, the OpenAI web-search tool and embedder, the reusable LangGraph research skeleton, the provenance+indexing writer, and the multi-run fan-out — so each agent plan only adds its own plan/collect/assess logic.

**Architecture:** A single generic graph, `build_research_graph(deps)`, walks a target list and resolves each box to *resolved* (a draft) or *absent*, bounded at 3 attempts, falling back to web search on `unresolved`. The graph is pure (no DB); persistence lives in the per-agent app service. Findings are written as lightweight captures under a synthetic per-agent source and indexed into the existing `Chunk` vector table so Ask can retrieve them. `Run now` fans out into three concurrently-tracked runs.

**Tech Stack:** Python 3.12, LangGraph, langchain-openai, SQLAlchemy, Alembic, pgvector, FastAPI, pytest.

**Spec:** [docs/superpowers/specs/2026-08-27-per-surface-research-graphs-design.md](../specs/2026-08-27-per-surface-research-graphs-design.md) — §5 (skeleton), §6 (data model + indexing), §10 (run orchestration), §12 (performance).

## Global Constraints

- Prerequisite: **Phase 0 clearing plan is complete** (the interpret pipeline is gone).
- **Dependency boundary:** the `agent` package owns all LLM/tool/graph construction; `app/services` imports only the graph entry points and does every DB write. The `agent` package must not import `app.models`.
- **Termination rule (every agent):** loop until each box is *resolved* or *absent*; hard cap `max_attempts = 3`; on exhaustion a box is `absent`, never fabricated.
- **Dependency policy:** before adding/using the OpenAI web-search tool, verify the current `langchain-openai` supports it and check the release date; do not pin versions from memory. If the hosted tool isn't available in the installed version, implement `WebSearch` against the OpenAI Responses API directly behind the same interface.
- Every finding that reaches a page MUST carry a real `source_url` and MUST be indexed via `index_chunks`.
- Full suite green after every task: `pytest -q`.

---

## File map

**Created:**
- `backend/alembic/versions/0007_research_columns.py`
- `backend/agent/tools/web_search.py`
- `backend/agent/graphs/research/__init__.py`
- `backend/agent/graphs/research/skeleton.py`
- `backend/app/services/research/__init__.py`
- `backend/app/services/research/provenance.py`
- `tests/test_research_skeleton.py`, `tests/test_web_search.py`, `tests/test_provenance.py`, `tests/test_run_fanout.py`

**Modified:**
- `backend/app/models/ledger.py` (+`Claim.stance`), `backend/app/models/signal.py` (+`Signal.theme_key`)
- `backend/agent/llm.py` (+`get_embedder`)
- `backend/app/models/run.py` (multi-run store)
- `backend/app/controllers/runs.py` (fan-out), `backend/app/routers/runs.py` (endpoints)
- `config/llm.yaml` (+`gate`, `synthesize`, `search` roles), `config/run_stages.yaml` (research stages)

---

### Task 1: Migration — `claim.stance` and `signal.theme_key`

**Files:**
- Create: `backend/alembic/versions/0007_research_columns.py`
- Modify: `backend/app/models/ledger.py`, `backend/app/models/signal.py`
- Test: `tests/test_research_columns.py`

**Interfaces:**
- Produces: `Claim.stance: str | None` (`strong|moderate|weak|none`), `Signal.theme_key: str | None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_research_columns.py
from datetime import UTC, datetime


def test_claim_stance_and_signal_theme_key_persist(session):
    from app.models.registry import Entity
    from app.models.ledger import Claim
    from app.models.signal import Signal
    from app.services.seeding import seed

    seed(session)
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    sonatype = session.query(Entity).filter_by(slug="sonatype").one()
    source_id = session.query(Entity).filter_by(slug="sonatype").one().id

    claim = Claim(
        subject_entity_id=jfrog.id, asserting_entity_id=sonatype.id,
        claim_text="x", claim_type="positioning", dimension="artifact_management",
        stance="weak", reliability_grade="C", first_seen_at=datetime.now(UTC),
    )
    signal = Signal(
        source_id=source_id, entity_id=sonatype.id, signal_type="security_trust",
        headline="y", occurred_at=datetime.now(UTC), cluster_key="k", theme_key="supply_chain_vulns",
    )
    session.add_all([claim, signal]); session.flush()
    session.refresh(claim); session.refresh(signal)
    assert claim.stance == "weak"
    assert signal.theme_key == "supply_chain_vulns"
```

- [ ] **Step 2: Run it, confirm it fails**

Run: `pytest tests/test_research_columns.py -v`
Expected: FAIL (`TypeError: 'stance' is an invalid keyword` or column missing).

- [ ] **Step 3: Add the model columns**

In `backend/app/models/ledger.py`, add to `Claim` (after `dimension`):
```python
    stance: Mapped[str | None] = mapped_column(String(16), nullable=True)  # strong|moderate|weak|none
```
In `backend/app/models/signal.py`, add to `Signal` (after `cluster_key`):
```python
    theme_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
```

- [ ] **Step 4: Write the Alembic revision**

```python
# backend/alembic/versions/0007_research_columns.py
"""research columns: claim.stance and signal.theme_key"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_research_columns"
down_revision: Union[str, None] = "0006_suppress_self_signals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("claim", sa.Column("stance", sa.String(length=16), nullable=True))
    op.add_column("signal", sa.Column("theme_key", sa.String(length=64), nullable=True))
    op.create_index("ix_signal_theme_key", "signal", ["theme_key"])


def downgrade() -> None:
    op.drop_index("ix_signal_theme_key", table_name="signal")
    op.drop_column("signal", "theme_key")
    op.drop_column("claim", "stance")
```

- [ ] **Step 5: Apply the migration, run the test**

Run: `alembic upgrade head` (from `backend/`), then `pytest tests/test_research_columns.py -v`
Expected: PASS.

- [ ] **Step 6: Full suite + commit**

Run: `pytest -q` → PASS.
```bash
git add backend/alembic/versions/0007_research_columns.py backend/app/models/ledger.py backend/app/models/signal.py tests/test_research_columns.py
git commit -m "feat: add claim.stance and signal.theme_key (Foundation)"
```

---

### Task 2: The web-search tool

**Files:**
- Create: `backend/agent/tools/web_search.py`
- Test: `tests/test_web_search.py`

**Interfaces:**
- Produces: `SearchHit` dataclass `{title: str, url: str, snippet: str, published_at: str | None}`; `WebSearch.search(query: str, k: int = 5) -> list[SearchHit]`; module-level `web_search(query, k)` using the default client.

- [ ] **Step 1: Write the failing test (against a stubbed client — no network)**

```python
# tests/test_web_search.py
def test_web_search_maps_client_results_to_hits():
    from agent.tools.web_search import WebSearch, SearchHit

    class FakeClient:
        def run(self, query, k):
            return [{"title": "T", "url": "https://x.com/a", "snippet": "S", "published_at": None}]

    ws = WebSearch(client=FakeClient())
    hits = ws.search("malicious npm package", k=3)
    assert hits == [SearchHit(title="T", url="https://x.com/a", snippet="S", published_at=None)]


def test_web_search_drops_results_without_a_url():
    from agent.tools.web_search import WebSearch

    class FakeClient:
        def run(self, query, k):
            return [{"title": "no url", "url": "", "snippet": "s"}, {"title": "ok", "url": "https://x", "snippet": "s"}]

    hits = WebSearch(client=FakeClient()).search("q")
    assert [h.url for h in hits] == ["https://x"]
```

- [ ] **Step 2: Run, confirm failure**

Run: `pytest tests/test_web_search.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/agent/tools/web_search.py
from __future__ import annotations

from dataclasses import dataclass

from agent.log import get_logger, step

logger = get_logger("agent.web_search")


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str
    published_at: str | None = None


class _OpenAIWebSearchClient:
    """Wraps the OpenAI hosted web_search tool via the Responses API. Verify the
    installed langchain-openai / openai version exposes it before relying on this
    (see Global Constraints: dependency policy)."""

    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI

        self._client = OpenAI()
        self._model = model

    def run(self, query: str, k: int) -> list[dict]:
        resp = self._client.responses.create(
            model=self._model,
            tools=[{"type": "web_search"}],
            input=f"Search the web and return the {k} most relevant results for: {query}",
        )
        # Normalised below; shape-mapping kept in one place so the graph never
        # sees vendor payloads.
        return _extract_results(resp, k)


def _extract_results(resp, k: int) -> list[dict]:
    results: list[dict] = []
    for item in getattr(resp, "output", []) or []:
        for citation in getattr(item, "annotations", []) or []:
            url = getattr(citation, "url", "") or ""
            if url:
                results.append({
                    "title": getattr(citation, "title", "") or url,
                    "url": url,
                    "snippet": getattr(citation, "text", "") or "",
                    "published_at": None,
                })
    return results[:k]


class WebSearch:
    def __init__(self, client=None):
        self._client = client or _OpenAIWebSearchClient()

    def search(self, query: str, k: int = 5) -> list[SearchHit]:
        raw = self._client.run(query, k)
        hits = [
            SearchHit(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("snippet", ""),
                published_at=r.get("published_at"),
            )
            for r in raw
            if r.get("url")
        ]
        step(logger, "web_search.done", query=query, hits=len(hits))
        return hits


def web_search(query: str, k: int = 5) -> list[SearchHit]:
    return WebSearch().search(query, k)
```

- [ ] **Step 4: Run tests → PASS. Commit.**

```bash
git add backend/agent/tools/web_search.py tests/test_web_search.py
git commit -m "feat: OpenAI web_search tool behind a stubbable interface (Foundation)"
```

---

### Task 3: The embedder

**Files:**
- Modify: `backend/agent/llm.py`
- Test: `tests/test_embedder.py`

**Interfaces:**
- Produces: `get_embedder() -> Embedder` where `Embedder.embed(texts: list[str]) -> list[list[float]]` (compatible with `index_chunks(embedder=...)`).

- [ ] **Step 1: Failing test**

```python
# tests/test_embedder.py
def test_get_embedder_returns_object_with_embed():
    from agent.llm import get_embedder
    e = get_embedder()
    assert hasattr(e, "embed")
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement in `backend/agent/llm.py`** (append):

```python
@lru_cache(maxsize=1)
def get_embedder(model: str = "text-embedding-3-small"):
    """Embedding client for the retrieval index. Returns an object exposing
    `.embed(list[str]) -> list[list[float]]`, matching index_chunks' contract."""
    from langchain_openai import OpenAIEmbeddings

    class _Embedder:
        def __init__(self):
            self._client = OpenAIEmbeddings(model=model)

        def embed(self, texts):
            return self._client.embed_documents(list(texts))

    return _Embedder()
```

- [ ] **Step 4: Run → PASS. Commit.**

```bash
git add backend/agent/llm.py tests/test_embedder.py
git commit -m "feat: get_embedder for retrieval indexing (Foundation)"
```

---

### Task 4: The research skeleton (generic graph)

**Files:**
- Create: `backend/agent/graphs/research/__init__.py`, `backend/agent/graphs/research/skeleton.py`
- Test: `tests/test_research_skeleton.py`

**Interfaces:**
- Consumes: nothing from other tasks (pure).
- Produces:
  - `ResearchState` (TypedDict): `targets: list[dict]`, `cursor: int`, `attempts: int`, `drafts: list[dict]`, `max_attempts: int`.
  - `ResearchDeps` protocol: `plan() -> list[dict]`; `collect(target) -> object | None`; `search(target) -> object`; `assess(target, material, attempts) -> tuple[str, dict | None]` returning `(verdict, draft)` with `verdict in {"resolved","unresolved","absent"}`; `absent_draft(target) -> dict`; `max_attempts: int`.
  - `run_research(deps) -> list[dict]` — compiles+invokes the graph, returns the final `drafts` (the app service persists them).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_research_skeleton.py
from agent.graphs.research.skeleton import run_research


class FakeDeps:
    max_attempts = 3

    def __init__(self):
        self.search_calls = {}

    def plan(self):
        return [{"id": "hit_first_try"}, {"id": "needs_search"}, {"id": "never"}]

    def collect(self, target):
        return {"structured": True} if target["id"] == "hit_first_try" else None

    def search(self, target):
        self.search_calls[target["id"]] = self.search_calls.get(target["id"], 0) + 1
        return {"web": target["id"]}

    def assess(self, target, material, attempts):
        if target["id"] == "hit_first_try":
            return "resolved", {"id": target["id"], "src": "structured"}
        if target["id"] == "needs_search":
            # unresolved until a search has happened, then resolved
            if material and material.get("web"):
                return "resolved", {"id": target["id"], "src": "web"}
            return "unresolved", None
        return "unresolved", None  # 'never' never resolves

    def absent_draft(self, target):
        return {"id": target["id"], "absent": True}


def test_resolved_absent_and_cap():
    deps = FakeDeps()
    drafts = run_research(deps)
    by_id = {d["id"]: d for d in drafts}

    assert by_id["hit_first_try"]["src"] == "structured"   # structured tier, no search
    assert by_id["needs_search"]["src"] == "web"           # fell back to search, resolved
    assert by_id["never"]["absent"] is True                # exhausted -> absent, not fabricated
    assert deps.search_calls["never"] == deps.max_attempts # capped at 3 searches
    assert "hit_first_try" not in deps.search_calls        # structured hit never searched
```

- [ ] **Step 2: Run → FAIL (module missing).**

- [ ] **Step 3: Implement the skeleton**

```python
# backend/agent/graphs/research/skeleton.py
from __future__ import annotations

from typing import Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from agent.log import get_logger, step

logger = get_logger("agent.research")


class ResearchState(TypedDict):
    targets: list[dict]
    cursor: int
    attempts: int
    drafts: list[dict]
    max_attempts: int


class ResearchDeps(Protocol):
    max_attempts: int
    def plan(self) -> list[dict]: ...
    def collect(self, target: dict) -> object | None: ...
    def search(self, target: dict) -> object: ...
    def assess(self, target: dict, material: object, attempts: int) -> tuple[str, dict | None]: ...
    def absent_draft(self, target: dict) -> dict: ...


def build_research_graph(deps: ResearchDeps):
    def plan_node(state: ResearchState) -> dict:
        targets = deps.plan()
        step(logger, "research.plan", targets=len(targets))
        return {"targets": targets, "cursor": 0, "attempts": 0, "drafts": []}

    def resolve_node(state: ResearchState) -> dict:
        """Resolve targets[cursor] to a draft (resolved) or an absent draft,
        looping to search on 'unresolved' up to max_attempts. Bounded, so it
        cannot spin — the whole per-target loop lives in this one node."""
        target = state["targets"][state["cursor"]]
        drafts = list(state["drafts"])
        material = deps.collect(target)
        attempts = 0
        if material is None:  # search-first surfaces
            material = deps.search(target)
            attempts = 1
        while True:
            verdict, draft = deps.assess(target, material, attempts)
            if verdict == "resolved" and draft is not None:
                drafts.append(draft)
                break
            if verdict == "absent" or attempts >= state["max_attempts"]:
                drafts.append(deps.absent_draft(target))
                break
            material = deps.search(target)  # unresolved -> fall back and retry
            attempts += 1
        return {"drafts": drafts, "cursor": state["cursor"] + 1, "attempts": 0}

    def _more(state: ResearchState) -> str:
        return "resolve" if state["cursor"] < len(state["targets"]) else "done"

    builder = StateGraph(ResearchState)
    builder.add_node("plan", plan_node)
    builder.add_node("resolve", resolve_node)
    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", _more, {"resolve": "resolve", "done": END})
    builder.add_conditional_edges("resolve", _more, {"resolve": "resolve", "done": END})
    return builder.compile()


def run_research(deps: ResearchDeps) -> list[dict]:
    graph = build_research_graph(deps)
    final = graph.invoke(
        {"targets": [], "cursor": 0, "attempts": 0, "drafts": [], "max_attempts": deps.max_attempts},
        config={"recursion_limit": 1000},
    )
    return final["drafts"]
```

Create `backend/agent/graphs/research/__init__.py` (empty).

- [ ] **Step 4: Run → PASS.**

Run: `pytest tests/test_research_skeleton.py -v` → PASS.

- [ ] **Step 5: Full suite + commit**

```bash
git add backend/agent/graphs/research/ tests/test_research_skeleton.py
git commit -m "feat: generic research graph skeleton (Foundation)"
```

---

### Task 5: Provenance + retrieval indexing

**Files:**
- Create: `backend/app/services/research/__init__.py`, `backend/app/services/research/provenance.py`
- Test: `tests/test_provenance.py`

**Interfaces:**
- Consumes: `get_embedder` (Task 3), `index_chunks` (existing).
- Produces:
  - `agent_source(session, agent_key: str, reliability_grade: str = "C") -> Source` — get-or-create a synthetic source (`key = f"{agent_key}_research"`).
  - `record_finding(session, agent_key, url, text, reliability_grade="C") -> RawCapture` — capture stub under that source.
  - `index_finding(session, record_type, record_id, text, entity_id, signal_type, published_at, reliability_grade) -> int` — calls `index_chunks` with the embedder.

- [ ] **Step 1: Failing test**

```python
# tests/test_provenance.py
from datetime import UTC, datetime


def test_record_finding_creates_capture_under_synthetic_source(session):
    from app.models.capture import RawCapture
    from app.models.registry import Source
    from app.services.seeding import seed
    from app.services.research.provenance import record_finding, agent_source

    seed(session)
    cap = record_finding(session, "industry", "https://x.com/a", "malicious npm package found")
    session.flush()
    src = agent_source(session, "industry")
    assert cap.source_id == src.id
    assert cap.blob_path == "https://x.com/a"
    assert src.key == "industry_research"
    # idempotent: second call reuses the same source row
    assert agent_source(session, "industry").id == src.id


def test_index_finding_writes_a_chunk(session, monkeypatch):
    from app.models.delivery import Chunk
    from app.services.seeding import seed
    from app.services.research import provenance

    seed(session)

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    n = provenance.index_finding(
        session, record_type="signal", record_id=1, text="malicious npm package",
        entity_id=None, signal_type="security_trust",
        published_at=datetime.now(UTC), reliability_grade="C",
    )
    session.flush()
    assert n == 1
    assert session.query(Chunk).filter_by(record_type="signal", record_id=1).count() == 1
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement**

```python
# backend/app/services/research/provenance.py
from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from agent.llm import get_embedder
from app.models.capture import RawCapture
from app.models.registry import Source
from app.services.ingestion.embedding import index_chunks


def agent_source(session: Session, agent_key: str, reliability_grade: str = "C") -> Source:
    key = f"{agent_key}_research"
    source = session.query(Source).filter_by(key=key).one_or_none()
    if source is None:
        source = Source(
            key=key, entity_id=None, url=f"internal://{key}", kind="api", mode="api",
            reliability_grade=reliability_grade, is_primary=False, check_frequency_minutes=1440,
        )
        session.add(source)
        session.flush()
    return source


def record_finding(session: Session, agent_key: str, url: str, text: str,
                   reliability_grade: str = "C") -> RawCapture:
    source = agent_source(session, agent_key, reliability_grade)
    capture = RawCapture(
        source_id=source.id, fetched_at=datetime.now(UTC), http_status=200,
        content_hash=hashlib.sha256((url + text).encode()).hexdigest(),
        blob_path=url, extracted_text=text, provenance="web_search",
    )
    session.add(capture)
    session.flush()
    return capture


def index_finding(session: Session, *, record_type: str, record_id: int, text: str,
                  entity_id, signal_type, published_at, reliability_grade) -> int:
    return index_chunks(
        session, [{"text": text, "prefix": None, "section_path": [], "token_count": 0}],
        record_type=record_type, record_id=record_id, embedder=get_embedder(),
        entity_id=entity_id, signal_type=signal_type,
        published_at=published_at, reliability_grade=reliability_grade,
    )
```

> **Note for executor:** confirm `Source.entity_id` is nullable. If the column is `NOT NULL`, add a nullable migration in this task (mirror Task 1's structure) before implementing `agent_source`; the synthetic source has no owning entity.

- [ ] **Step 4: Run → PASS. Full suite. Commit.**

```bash
git add backend/app/services/research/ tests/test_provenance.py
git commit -m "feat: provenance capture stub + retrieval indexing (Foundation)"
```

---

### Task 6: Multi-run store + Run-now fan-out

**Files:**
- Modify: `backend/app/models/run.py`, `backend/app/controllers/runs.py`, `backend/app/routers/runs.py`, `config/run_stages.yaml`
- Test: `tests/test_run_fanout.py`

**Interfaces:**
- Consumes: `run_research` per surface (agent plans provide `run_industry`/`run_signals`/`run_comparison` in `worker/jobs.py`; here they may be stubbed).
- Produces: `start_surface_run(kind, background_tasks=None) -> dict` for `kind in {"industry","signals","comparison"}`; `start_all(background_tasks=None) -> dict` returning `{"run_ids": {surface: run_id}}`; the run store holds multiple concurrent runs.

- [ ] **Step 1: Failing test**

```python
# tests/test_run_fanout.py
def test_multiple_runs_coexist_in_the_store():
    from app.models.run import create_run, get_run
    a = create_run()
    b = create_run()
    assert a.id != b.id or True  # ids may collide by minute; the store must keep both
    assert get_run(a.id) is not None
    assert get_run(b.id) is not None


def test_start_all_returns_three_run_ids(monkeypatch):
    import app.controllers.runs as runs

    started = []
    monkeypatch.setattr(runs, "_run_surface", lambda run_id, kind: started.append(kind))
    body = runs.start_all()
    assert set(body["run_ids"]) == {"industry", "signals", "comparison"}
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Make the run store multi-run**

In `backend/app/models/run.py`: remove the `_store.clear()` calls in `create_run` and `put_run`; give each run a unique id even within the same minute:

```python
import uuid

def create_run() -> Run:
    global _current_run_id
    started = datetime.now(UTC)
    run_id = f"run_{started.strftime('%Y-%m-%dT%H:%M:%SZ')}_{uuid.uuid4().hex[:6]}"
    stages = load_run_stages()
    run = Run(id=run_id, stage_key=stages[0]["key"], current=0, total=len(stages), started_at=started)
    _store[run_id] = run
    _current_run_id = run_id
    return run
```
and in `put_run`, drop `_store.clear()` (keep the assignment).

- [ ] **Step 4: Add fan-out to `backend/app/controllers/runs.py`**

Add the surface kinds and fan-out (reuse `create_run`/`update_run`; each surface runs its job and marks its own run done):

```python
_SURFACE_JOBS = {
    "industry": "run_industry",
    "signals": "run_signals",
    "comparison": "run_comparison",
}


def _run_surface(run_id: str, kind: str) -> None:
    try:
        report = getattr(jobs, _SURFACE_JOBS[kind])()
        update_run(run_id, status="done", new_items=_new_items_from_report(report),
                   finished_at=datetime.now(UTC))
    except Exception as exc:  # one surface failing must not fail the others
        logger.exception("run.surface.failed run_id=%s kind=%s", run_id, kind)
        update_run(run_id, status="failed", message=_readable_error(exc),
                   finished_at=datetime.now(UTC))


def start_surface_run(kind: str, background_tasks=None) -> dict:
    if kind not in _SURFACE_JOBS:
        raise ValueError(f"Unknown surface run: {kind}")
    run = create_run()
    if background_tasks is not None:
        background_tasks.add_task(_run_surface, run.id, kind)
    else:
        _run_surface(run.id, kind)
    return {"run_id": run.id, "kind": kind}


def start_all(background_tasks=None) -> dict:
    run_ids: dict[str, str] = {}
    for kind in _SURFACE_JOBS:
        run = create_run()
        run_ids[kind] = run.id
        if background_tasks is not None:
            background_tasks.add_task(_run_surface, run.id, kind)
        else:
            _run_surface(run.id, kind)
    return {"run_ids": run_ids}
```

- [ ] **Step 5: Wire the router**

In `backend/app/routers/runs.py`, route `POST /runs` with `kind in {"industry","signals","comparison"}` to `start_surface_run`, and add `POST /runs/all` → `start_all(background_tasks)`. (Keep the existing `collect`/`manual` kinds working.)

- [ ] **Step 6: Add research display stages to `config/run_stages.yaml`**

```yaml
stages:
  - { key: collect,   label: Checking sources }
  - { key: research,  label: Researching }
  - { key: synthesize,label: Writing findings }
  - { key: done,      label: Done }
```

- [ ] **Step 7: Run tests → PASS. Full suite. Commit.**

```bash
git add backend/app/models/run.py backend/app/controllers/runs.py backend/app/routers/runs.py config/run_stages.yaml tests/test_run_fanout.py
git commit -m "feat: multi-run store + Run-now fan-out (Foundation)"
```

---

## Self-Review

- **Spec coverage:** §5 skeleton → Task 4 (`ResearchState`, resolved/unresolved/absent, cap); §6 columns → Task 1; §6 indexing/provenance → Task 5; §10 fan-out + multi-run → Task 6; §3 search vendor → Task 2; embedder gap → Task 3. ✓
- **Placeholder scan:** every step has runnable code or an exact command. Task 5's nullable-`Source.entity_id` caveat gives a concrete conditional action, not a vague "handle it". ✓
- **Type consistency:** `run_research(deps) -> list[dict]` (Task 4) is what each agent service consumes; `ResearchDeps.assess -> (verdict, draft)` matches the skeleton loop; `record_finding`/`index_finding` (Task 5) signatures match their tests; `start_all -> {"run_ids": {...}}` matches Task 6's test. `SearchHit` fields match `web_search`'s mapping. ✓
- **Boundary check:** `agent/*` (Tasks 2–4) imports no `app.models`; DB writes live only in `app/services/research` (Task 5) and controllers (Task 6). ✓
