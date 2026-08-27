# Industry Agent: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A search-first LangGraph agent that fills the Industry radar with DevSecOps-relevant cards only — four fixed buckets, a strict LLM relevance gate whose `exclude` list drops model/RAG noise, and "keep nothing" as a valid outcome.

**Architecture:** One `run_research` target per bucket. `collect` returns `None` (no structured feed) so every bucket goes straight to web search; `assess` is the relevance gate — it keeps on-topic hits and returns them as an `items[]` list, retries with a broadened query when it keeps nothing, and resolves to empty (absent) after the cap. The service persists each kept item as a `Signal` on the `industry` entity tagged with `theme_key`, indexed for Ask.

**Tech Stack:** Python 3.12, LangGraph, langchain-openai (structured output), SQLAlchemy, pytest.

**Spec:** [.../2026-08-27-per-surface-research-graphs-design.md](../specs/2026-08-27-per-surface-research-graphs-design.md) — §7.

## Global Constraints

- Prerequisite: **Foundation plan complete** (`run_research`, `record_finding`, `index_finding`, `agent_source`, `web_search`, `get_model`, `get_embedder`).
- Every card carries a real `source_url`; **empty is valid** — if the gate keeps nothing, write nothing.
- The gate reasons per-hit against the bucket's `include`/`exclude`; the `exclude` list is authoritative (model-quality news is dropped).
- Suite green after each task: `pytest -q`.

## File map

**Created:** `config/industry_buckets.yaml`, `backend/agent/graphs/research/industry/__init__.py`, `backend/agent/graphs/research/industry/deps.py`, `backend/agent/prompts/research_industry.md`, `backend/app/services/research/industry_agent.py`, tests.
**Modified:** `backend/worker/jobs.py` (+`run_industry`), `backend/app/services/industry_themes.py` (group by `theme_key`), `config/llm.yaml` (+`gate` role), `tests/test_industry_themes.py`, `client/src/pages/Industry.tsx` (+Run-this-page button).

---

### Task 1: The buckets config + LLM `gate` role

**Files:**
- Create: `config/industry_buckets.yaml`
- Modify: `config/llm.yaml`
- Test: `tests/test_industry_buckets.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_industry_buckets.py
def test_industry_buckets_load_with_include_and_exclude():
    from app.services.research.industry_agent import load_buckets
    buckets = load_buckets()
    keys = {b["key"] for b in buckets}
    assert keys == {"supply_chain_vulns", "ai_secops", "pipeline_devsecops", "regulation_compliance"}
    ai = next(b for b in buckets if b["key"] == "ai_secops")
    assert "quantization" in ai["exclude"]      # model-quality news is out
    assert "poisoned model" in ai["include"]     # AI supply-chain security is in
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Write `config/industry_buckets.yaml`** (verbatim from spec §7 — the four buckets with `key/label/signal_type/include/exclude/jfrog_relevance`).

- [ ] **Step 4: Add the `gate` role to `config/llm.yaml`** — a small, low-latency model with tight timeout (mirror the existing `extract` block's shape; set `reasoning_effort: low`, a short `timeout_seconds`). Add a `synthesize` role too (used later by Signals/Comparison) if not present.

- [ ] **Step 5: Implement `load_buckets`** in `backend/app/services/research/industry_agent.py`:

```python
from pathlib import Path
import yaml
from app.settings import settings


def load_buckets() -> list[dict]:
    data = yaml.safe_load((Path(settings.config_dir) / "industry_buckets.yaml").read_text(encoding="utf-8"))
    return data["buckets"]
```

- [ ] **Step 6: Run → PASS. Commit.**

```bash
git add config/industry_buckets.yaml config/llm.yaml backend/app/services/research/industry_agent.py tests/test_industry_buckets.py
git commit -m "feat: industry buckets config + gate LLM role (Industry)"
```

---

### Task 2: The relevance gate (deps.assess)

The gate is the noise fix. Test it with a **stubbed LLM** so no network is needed and the include/exclude behavior is pinned.

**Files:**
- Create: `backend/agent/graphs/research/industry/deps.py`, `backend/agent/prompts/research_industry.md`
- Test: `tests/test_industry_deps.py`

**Interfaces:**
- Produces: `IndustryDeps(buckets, gate_model, search)` implementing `ResearchDeps`; `assess(target, hits, attempts) -> (verdict, draft)` where a resolved draft is `{"bucket": key, "signal_type": st, "items": [{"headline","body","why_it_matters","source_url"}]}`.

- [ ] **Step 1: Failing test**

```python
# tests/test_industry_deps.py
from agent.graphs.research.industry.deps import IndustryDeps
from agent.tools.web_search import SearchHit


class StubGate:
    """Returns whatever items the test wants, ignoring the prompt."""
    def __init__(self, items):
        self._items = items
    def invoke(self, _prompt):
        from agent.graphs.research.industry.deps import IndustryAssessment
        return IndustryAssessment(kept=self._items)


def _bucket():
    return {"key": "ai_secops", "label": "AI Sec", "signal_type": "security_trust",
            "include": ["poisoned model"], "exclude": ["quantization"], "jfrog_relevance": "x"}


def test_gate_keeps_on_topic_items_and_resolves():
    from agent.graphs.research.industry.deps import IndustryItem
    items = [IndustryItem(headline="Malicious model on HF", body="b", why_it_matters="w",
                          source_url="https://x/a")]
    deps = IndustryDeps([_bucket()], gate_model=StubGate(items), search=lambda t: [])
    verdict, draft = deps.assess(_bucket(), [SearchHit("t", "https://x/a", "s")], attempts=1)
    assert verdict == "resolved"
    assert draft["items"][0]["source_url"] == "https://x/a"
    assert draft["bucket"] == "ai_secops"


def test_gate_keeping_nothing_is_unresolved_then_absent():
    deps = IndustryDeps([_bucket()], gate_model=StubGate([]), search=lambda t: [])
    verdict, draft = deps.assess(_bucket(), [SearchHit("t", "https://x/a", "s")], attempts=1)
    assert verdict == "unresolved"     # nothing kept, but attempts remain -> retry
    assert draft is None


def test_absent_draft_is_empty_items():
    deps = IndustryDeps([_bucket()], gate_model=StubGate([]), search=lambda t: [])
    assert deps.absent_draft(_bucket()) == {"bucket": "ai_secops", "signal_type": "security_trust", "items": []}
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `deps.py`**

```python
# backend/agent/graphs/research/industry/deps.py
from __future__ import annotations

import json

from pydantic import BaseModel

from agent.llm import prompt as load_prompt
from agent.tools.web_search import SearchHit, web_search


class IndustryItem(BaseModel):
    headline: str
    body: str
    why_it_matters: str
    source_url: str


class IndustryAssessment(BaseModel):
    kept: list[IndustryItem]


class IndustryDeps:
    max_attempts = 3

    def __init__(self, buckets, gate_model, search=None):
        self._buckets = buckets
        self._gate = gate_model
        self._search = search or (lambda target: web_search(self._query(target), k=6))

    def _query(self, target: dict) -> str:
        return f'{target["label"]} ({" OR ".join(target["include"])})'

    def plan(self) -> list[dict]:
        return list(self._buckets)

    def collect(self, target: dict):
        return None  # search-first

    def search(self, target: dict):
        return self._search(target)

    def assess(self, target: dict, hits, attempts: int):
        payload = {
            "bucket": target["key"], "include": target["include"], "exclude": target["exclude"],
            "hits": [{"title": h.title, "url": h.url, "snippet": h.snippet} for h in hits],
        }
        prompt_text = load_prompt("research_industry") + "\n\nDATA:\n" + json.dumps(payload)
        result: IndustryAssessment = self._gate.invoke(prompt_text)
        kept = [i for i in result.kept if i.source_url]
        if kept:
            return "resolved", {
                "bucket": target["key"], "signal_type": target["signal_type"],
                "items": [i.model_dump() for i in kept],
            }
        return "unresolved", None

    def absent_draft(self, target: dict):
        return {"bucket": target["key"], "signal_type": target["signal_type"], "items": []}
```

Create `backend/agent/graphs/research/industry/__init__.py` (empty), and `research_industry.md` — the strict system prompt: "You are the Industry relevance gate. Keep ONLY hits that belong to this DevSecOps bucket. The `exclude` list is authoritative — drop model-quality/benchmark/RAG-technique news even if it mentions security. For each kept hit return headline, a body (trend + implication), a why_it_matters line tying it to JFrog, and the source_url. Keep nothing rather than force a match."

- [ ] **Step 4: Run → PASS. Commit.**

```bash
git add backend/agent/graphs/research/industry/ backend/agent/prompts/research_industry.md tests/test_industry_deps.py
git commit -m "feat: industry relevance gate deps (Industry)"
```

---

### Task 3: Persist findings + `run_industry`

**Files:**
- Modify: `backend/app/services/research/industry_agent.py`, `backend/worker/jobs.py`
- Test: `tests/test_industry_agent.py`

**Interfaces:**
- Consumes: `run_research`, `record_finding`, `index_finding`, `score`, `cluster_key`.
- Produces: `run_industry() -> dict` (report `{"industry_items": n}`); `persist_industry(session, drafts) -> int`.

- [ ] **Step 1: Failing test (drafts in, Signals out, indexed)**

```python
# tests/test_industry_agent.py
def test_persist_industry_writes_signals_with_theme_key_and_indexes(session, monkeypatch):
    from app.models.registry import Entity
    from app.models.signal import Signal
    from app.models.delivery import Chunk
    from app.services.seeding import seed
    from app.services.research import industry_agent, provenance

    seed(session)

    class FakeEmbedder:
        def embed(self, texts): return [[0.0] * 1536 for _ in texts]
    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())

    drafts = [{
        "bucket": "supply_chain_vulns", "signal_type": "security_trust",
        "items": [{"headline": "Malicious npm pkg", "body": "b", "why_it_matters": "w",
                   "source_url": "https://x/a"}],
    }, {
        "bucket": "ai_secops", "signal_type": "security_trust", "items": [],  # absent bucket
    }]

    n = industry_agent.persist_industry(session, drafts)
    session.flush()

    industry = session.query(Entity).filter_by(slug="industry").one()
    sigs = session.query(Signal).filter_by(entity_id=industry.id).all()
    assert n == 1 and len(sigs) == 1
    assert sigs[0].theme_key == "supply_chain_vulns"
    assert sigs[0].why_it_matters == "w"
    assert session.query(Chunk).filter_by(record_type="signal", record_id=sigs[0].id).count() == 1
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `persist_industry` + `run_industry`**

```python
# add to backend/app/services/research/industry_agent.py
from datetime import UTC, datetime
import hashlib

from sqlalchemy.orm import Session

from app.config.loader import load_config
from app.db.session import SessionLocal
from app.models.registry import Entity
from app.models.signal import Signal, SignalEvidence
from app.services.research.provenance import record_finding, index_finding
from app.services.scoring.materiality import score


def persist_industry(session: Session, drafts: list[dict]) -> int:
    industry = session.query(Entity).filter_by(slug="industry").one()
    cfg = load_config()
    now = datetime.now(UTC)
    written = 0
    for draft in drafts:
        for item in draft["items"]:
            capture = record_finding(session, "industry", item["source_url"],
                                     f'{item["headline"]}\n{item["body"]}')
            facets = {
                "signal_type": draft["signal_type"], "subject_entity": None,
                "asserting_entity": "industry", "entity_tier": industry.tier,
                "reliability_grade": "C", "corroboration_count": 1, "capability_tags": [],
                "occurred_at": now, "text": item["body"],
            }
            signal = Signal(
                source_id=capture.source_id, entity_id=industry.id,
                signal_type=draft["signal_type"], theme_key=draft["bucket"],
                headline=item["headline"][:256], occurred_at=now,
                cluster_key=hashlib.sha256((draft["bucket"] + item["headline"]).encode()).hexdigest()[:128],
                so_what_product=item["body"], why_it_matters=item["why_it_matters"],
                score_sales=score(facets, "sales", cfg).total,
                score_product=score(facets, "product", cfg).total,
                score_exec=score(facets, "exec", cfg).total,
            )
            session.add(signal); session.flush()
            session.add(SignalEvidence(signal_id=signal.id, capture_id=capture.id,
                                       quote=item["headline"], quote_offset=0, match_method="synthesis"))
            index_finding(session, record_type="signal", record_id=signal.id, text=item["body"],
                          entity_id=industry.id, signal_type=draft["signal_type"],
                          published_at=now, reliability_grade="C")
            written += 1
    return written


def run_industry() -> dict:
    from agent.graphs.research.skeleton import run_research
    from agent.graphs.research.industry.deps import IndustryDeps
    from agent.llm import get_model
    from agent.graphs.research.industry.deps import IndustryAssessment

    gate = get_model("gate").with_structured_output(IndustryAssessment, strict=True)
    deps = IndustryDeps(load_buckets(), gate_model=gate)
    drafts = run_research(deps)
    with SessionLocal() as session:
        n = persist_industry(session, drafts)
        session.commit()
    return {"industry_items": n}
```

Add `run_industry` re-export to `worker/jobs.py`:
```python
from app.services.research.industry_agent import run_industry  # noqa: F401
```

- [ ] **Step 4: Run → PASS. Full suite. Commit.**

```bash
git add backend/app/services/research/industry_agent.py backend/worker/jobs.py tests/test_industry_agent.py
git commit -m "feat: persist industry findings + run_industry (Industry)"
```

---

### Task 4: Read path — group the Industry page by `theme_key`

Replaces the deferred `themes.yaml` keyword routing (Phase 0 left it in place).

**Files:**
- Modify: `backend/app/services/industry_themes.py`, `tests/test_industry_themes.py`
- Delete: `config/themes.yaml`

- [ ] **Step 1: Update the test** to seed two industry signals with `theme_key` set and assert `list_themes` groups them by bucket label from `industry_buckets.yaml` (replace the old `assign_theme` keyword tests).

- [ ] **Step 2: Rewrite `industry_themes.py`** so `list_themes`/`theme_detail` read `industry_buckets.yaml` for labels/`jfrog_relevance` and group `fetch_active_industry_signals` by `Signal.theme_key` (drop `_load_themes`, `assign_theme`, `_routing_item`). Fall back to an "Other" bucket for `theme_key is None`.

- [ ] **Step 3: `git rm config/themes.yaml`.**

- [ ] **Step 4: Run → PASS. Commit.**

```bash
git add backend/app/services/industry_themes.py tests/test_industry_themes.py config/themes.yaml
git commit -m "refactor: industry page groups by theme_key, drop themes.yaml (Industry)"
```

---

### Task 5: Frontend — "Run this page" on Industry

**Files:**
- Modify: `client/src/pages/Industry.tsx`, `client/src/api/client.ts`
- Test: `client/src/pages/industry.test.tsx`

- [ ] **Step 1: Add `runSurface(kind)`** to `client/src/api/client.ts` → `POST /runs {kind}` returning `{run_id}`, plus a poll of `GET /runs/{run_id}` (reuse existing run-progress polling if present).

- [ ] **Step 2: Add a `Run this page` button** to `Industry.tsx` that calls `runSurface("industry")` and refreshes the theme list on completion. Follow the existing Today `Run now` button pattern.

- [ ] **Step 3: Update `industry.test.tsx`** to assert the button posts `kind: "industry"` (mock the client).

- [ ] **Step 4: Run `npm test` (client) → PASS. Commit.**

```bash
git add client/src/pages/Industry.tsx client/src/api/client.ts client/src/pages/industry.test.tsx
git commit -m "feat(client): Run-this-page button on Industry (Industry)"
```

---

## Self-Review

- **Spec coverage (§7):** 4 buckets + include/exclude → Task 1; relevance gate with exclude authoritative + empty-valid → Task 2; persist Signals with `theme_key` + indexing → Task 3; read path by `theme_key` → Task 4; Run-this-page → Task 5. ✓
- **Placeholder scan:** gate and persistence have full code; the prompt content is specified; Task 4/5 steps name exact files and the pattern to follow. ✓
- **Type consistency:** `IndustryDeps.assess -> (verdict, draft)` and `absent_draft -> {"items":[]}` match the skeleton contract from Foundation Task 4; `persist_industry(session, drafts)` consumes exactly the draft shape `assess` produces; `run_industry -> {"industry_items": n}` feeds `_new_items_from_report` via a keyed count. ✓
