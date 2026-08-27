# Signals Agent: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tiered LangGraph agent that fills the Signals page for each competitor across hiring, pricing, funding, and security-advisory sub-types — trying a structured source first, letting the LLM judge usability, and falling back to web search only when needed.

**Architecture:** One `run_research` target per `(competitor, sub_type)`. `collect` (injected by the app service, since it touches the DB/adapters) returns structured records for hiring (Lever/Greenhouse) and security_advisory (OSV) when a source exists, else `None`; the LLM `assess` gate judges usability and synthesizes the card; `unresolved` falls back to web search. Drafts persist as `Signal`s on the competitor entity, indexed for Ask.

**Tech Stack:** Python 3.12, LangGraph, langchain-openai, SQLAlchemy, pytest.

**Spec:** [.../2026-08-27-per-surface-research-graphs-design.md](../specs/2026-08-27-per-surface-research-graphs-design.md) — §8 (Signals), §11 (OSV fold-in = decision A).

## Global Constraints

- Prerequisite: **Foundation complete.** (Industry is independent; do it first only for sequencing.)
- **Boundary:** structured collection (DB + adapters) lives in `app/services`, injected into the graph deps as a callable. The `agent` package stays DB-free.
- Sub-type → `signal_type`: hiring → `talent_org`, pricing → `pricing_packaging`, funding → `corporate_financial`, security_advisory → `security_trust`.
- Every card has a `source_url` and a `why_it_matters` line, or it doesn't ship. Pricing/funding have no adapter → straight to search.
- Suite green after each task: `pytest -q`.

## File map

**Created:** `config/competitors.yaml`, `backend/agent/graphs/research/signals/{__init__,deps}.py`, `backend/agent/prompts/research_signals.md`, `backend/app/services/research/signals_agent.py`, tests.
**Modified:** `config/entities.yaml` (+snyk/aqua/checkmarx), `backend/worker/jobs.py` (+`run_signals`), `client/src/pages/Signals.tsx`, `client/src/api/client.ts`.

---

### Task 1: Competitor set (entities + allowlist)

Establishes the GitHub/Sonatype/Snyk/Aqua/Checkmarx set that Signals **and** Comparison use.

**Files:**
- Modify: `config/entities.yaml`
- Create: `config/competitors.yaml`
- Test: `tests/test_competitors.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_competitors.py
def test_active_competitor_set():
    from app.services.research.competitors import load_competitors
    slugs = {c["slug"] for c in load_competitors()}
    assert slugs == {"github", "sonatype", "snyk", "aqua", "checkmarx"}
    aqua = next(c for c in load_competitors() if c["slug"] == "aqua")
    assert "Trivy" in aqua["aliases"]
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Add entities** to `config/entities.yaml`:
```yaml
  - { slug: snyk,      name: Snyk,            kind: competitor, tier: 2, aliases: [] }
  - { slug: aqua,      name: Aqua Security,   kind: competitor, tier: 2, aliases: [Trivy] }
  - { slug: checkmarx, name: Checkmarx,       kind: competitor, tier: 2, aliases: ["Checkmarx One"] }
```

- [ ] **Step 4: Create `config/competitors.yaml`** (the grid allowlist — decouples "tracked competitors" from "all entities so gitlab/harbor/azure stay as entities but off the grid"):
```yaml
competitors: [github, sonatype, snyk, aqua, checkmarx]
```

- [ ] **Step 5: Implement `load_competitors`** in `backend/app/services/research/competitors.py`:
```python
from pathlib import Path
import yaml
from app.settings import settings


def load_competitors() -> list[dict]:
    cfg_dir = Path(settings.config_dir)
    allow = yaml.safe_load((cfg_dir / "competitors.yaml").read_text(encoding="utf-8"))["competitors"]
    entities = yaml.safe_load((cfg_dir / "entities.yaml").read_text(encoding="utf-8"))["entities"]
    by_slug = {e["slug"]: e for e in entities}
    return [{"slug": s, "name": by_slug[s]["name"], "aliases": by_slug[s].get("aliases", [])} for s in allow]
```

- [ ] **Step 6: Run → PASS. Commit.**

```bash
git add config/entities.yaml config/competitors.yaml backend/app/services/research/competitors.py tests/test_competitors.py
git commit -m "feat: active competitor set (github/sonatype/snyk/aqua/checkmarx) (Signals)"
```

> **Note:** any test asserting a fixed competitor/entity count (e.g. `test_config`, seeding tests) must be updated to include the three new entities. Run `pytest -q` and fix the counts as part of this task.

---

### Task 2: Signals deps — tiered structured → gate → search

**Files:**
- Create: `backend/agent/graphs/research/signals/{__init__,deps}.py`, `backend/agent/prompts/research_signals.md`
- Test: `tests/test_signals_deps.py`

**Interfaces:**
- Produces: `SignalsDeps(targets, structured_fn, search_fn, gate_model)` implementing `ResearchDeps`. `structured_fn(target) -> list | None`; `search_fn(target) -> list[SearchHit]`; `assess(target, material, attempts) -> (verdict, draft)`; resolved draft `{"competitor","signal_type","headline","so_what","why_it_matters","tags","source_url"}`; `absent_draft(target) -> {"competitor","sub_type","absent": True}`.

- [ ] **Step 1: Failing test — pins the tiering**

```python
# tests/test_signals_deps.py
from agent.graphs.research.signals.deps import SignalsDeps, SignalCard


def _t(sub="hiring"):
    return {"competitor": "sonatype", "name": "Sonatype", "aliases": ["Nexus"],
            "sub_type": sub, "signal_type": "talent_org"}


class StubGate:
    def __init__(self, usable): self.usable = usable
    def invoke(self, _p):
        if self.usable:
            return SignalCard(usable=True, headline="18 EMEA sales roles", so_what="GTM push",
                              why_it_matters="hits JFrog's strongest segment", tags=["SALES"],
                              source_url="https://x/jobs")
        return SignalCard(usable=False, headline="", so_what="", why_it_matters="", tags=[], source_url="")


def test_structured_hit_resolves_without_search():
    calls = []
    deps = SignalsDeps([_t()], structured_fn=lambda t: [{"title": "role"}],
                       search_fn=lambda t: calls.append(t) or [], gate_model=StubGate(True))
    material = deps.collect(_t())
    assert material == [{"title": "role"}]
    verdict, draft = deps.assess(_t(), material, attempts=0)
    assert verdict == "resolved" and draft["source_url"] == "https://x/jobs"
    assert calls == []  # never fell back to search


def test_no_structured_source_returns_none_so_skeleton_searches():
    deps = SignalsDeps([_t("pricing")], structured_fn=lambda t: None,
                       search_fn=lambda t: [], gate_model=StubGate(True))
    assert deps.collect(_t("pricing")) is None


def test_not_usable_is_unresolved():
    deps = SignalsDeps([_t()], structured_fn=lambda t: [{"x": 1}],
                       search_fn=lambda t: [], gate_model=StubGate(False))
    verdict, draft = deps.assess(_t(), [{"x": 1}], attempts=1)
    assert verdict == "unresolved" and draft is None
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `deps.py`**

```python
# backend/agent/graphs/research/signals/deps.py
from __future__ import annotations

import json

from pydantic import BaseModel

from agent.llm import prompt as load_prompt


class SignalCard(BaseModel):
    usable: bool
    headline: str
    so_what: str
    why_it_matters: str
    tags: list[str]
    source_url: str


class SignalsDeps:
    max_attempts = 3

    def __init__(self, targets, structured_fn, search_fn, gate_model):
        self._targets = targets
        self._structured = structured_fn
        self._search = search_fn
        self._gate = gate_model

    def plan(self):
        return list(self._targets)

    def collect(self, target):
        return self._structured(target)  # None when no structured source exists

    def search(self, target):
        return self._search(target)

    def assess(self, target, material, attempts):
        payload = {
            "competitor": target["name"], "aliases": target["aliases"], "sub_type": target["sub_type"],
            "material": _as_json(material),
        }
        prompt_text = load_prompt("research_signals") + "\n\nDATA:\n" + json.dumps(payload)
        card: SignalCard = self._gate.invoke(prompt_text)
        if card.usable and card.source_url and card.why_it_matters:
            return "resolved", {
                "competitor": target["competitor"], "signal_type": target["signal_type"],
                "headline": card.headline, "so_what": card.so_what,
                "why_it_matters": card.why_it_matters, "tags": card.tags, "source_url": card.source_url,
            }
        return "unresolved", None

    def absent_draft(self, target):
        return {"competitor": target["competitor"], "sub_type": target["sub_type"], "absent": True}


def _as_json(material):
    if material is None:
        return []
    out = []
    for m in material:
        if hasattr(m, "url"):  # SearchHit
            out.append({"title": m.title, "url": m.url, "snippet": m.snippet})
        else:
            out.append(m)
    return out
```

Create `__init__.py` (empty) and `research_signals.md`: "You assess one competitor sub-type. Decide if the material yields a genuine signal about THIS competitor and sub-type, recent and real. If yes, write a headline, an intent-read (so_what), a why_it_matters line tying it to JFrog, tags (SALES/EXEC/…), and the source_url. If the material is empty, off-topic, stale, or not about this competitor, set usable=false."

- [ ] **Step 4: Run → PASS. Commit.**

```bash
git add backend/agent/graphs/research/signals/ backend/agent/prompts/research_signals.md tests/test_signals_deps.py
git commit -m "feat: signals tiered deps (structured -> gate -> search) (Signals)"
```

---

### Task 3: App service — structured_fn (incl. OSV), persist, `run_signals`

**Files:**
- Create/modify: `backend/app/services/research/signals_agent.py`
- Modify: `backend/worker/jobs.py`
- Test: `tests/test_signals_agent.py`

**Interfaces:**
- Produces: `build_targets() -> list[dict]` (competitors × sub-types); `structured_for(session)(target) -> list | None`; `persist_signals(session, drafts) -> int`; `run_signals() -> dict`.

- [ ] **Step 1: Failing test — structured_fn tiering + persistence**

```python
# tests/test_signals_agent.py
def test_structured_for_uses_lever_when_a_jobs_source_exists(session):
    from app.services.seeding import seed
    from app.services.research.signals_agent import structured_for
    seed(session)
    fn = structured_for(session, fetcher=_FakeFetcher())
    hiring = {"competitor": "sonatype", "sub_type": "hiring", "signal_type": "talent_org"}
    pricing = {"competitor": "sonatype", "sub_type": "pricing", "signal_type": "pricing_packaging"}
    assert fn(hiring) is not None      # sonatype_jobs (Lever) exists
    assert fn(pricing) is None         # no pricing adapter -> skeleton will search


def test_persist_signals_writes_cards_and_indexes(session, monkeypatch):
    from app.models.registry import Entity
    from app.models.signal import Signal
    from app.services.seeding import seed
    from app.services.research import signals_agent, provenance
    seed(session)
    class FakeEmbedder:
        def embed(self, texts): return [[0.0]*1536 for _ in texts]
    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    drafts = [
        {"competitor": "sonatype", "signal_type": "talent_org", "headline": "h", "so_what": "s",
         "why_it_matters": "w", "tags": ["SALES"], "source_url": "https://x/a"},
        {"competitor": "snyk", "sub_type": "pricing", "absent": True},  # skipped
    ]
    n = signals_agent.persist_signals(session, drafts)
    session.flush()
    sonatype = session.query(Entity).filter_by(slug="sonatype").one()
    assert n == 1
    assert session.query(Signal).filter_by(entity_id=sonatype.id, signal_type="talent_org").count() == 1
```
(`_FakeFetcher` returns a Lever-shaped JSON body for the jobs URL; mirror `ScriptedFeedFetcher` in `tests/test_jobs.py`.)

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `signals_agent.py`**

Build targets from `load_competitors()` × sub-types; implement `structured_for(session, fetcher)` returning a closure that: for `hiring` looks up a `Source` for that competitor whose `adapter in {lever, greenhouse}` and runs it; for `security_advisory` runs the `osv` source (OSV fold-in, decision A); for `pricing`/`funding` returns `None`. `persist_signals` skips `absent` drafts and, for each card, writes `record_finding` + `Signal(entity=competitor, signal_type, headline, so_what_sales/product/exec=so_what, why_it_matters, capability_tags=tags, occurred_at=now, cluster_key=hash)` + `SignalEvidence(match_method="synthesis")` + `score()` + `index_finding`. `run_signals()` wires `SignalsDeps(build_targets(), structured_for(session,...), search_fn=lambda t: web_search(_query(t)), gate)` and persists. Re-export `run_signals` in `worker/jobs.py`.

Provide `_query(target)` per sub-type, e.g. hiring → `f'{name} careers {" ".join(aliases)} enterprise sales OR security engineer'`; pricing → `f'{name} pricing plans per-seat'`; funding → `f'{name} funding round OR acquisition 2026'`.

- [ ] **Step 4: Run → PASS. Full suite. Commit.**

```bash
git add backend/app/services/research/signals_agent.py backend/worker/jobs.py tests/test_signals_agent.py
git commit -m "feat: signals structured_fn (incl OSV), persist, run_signals (Signals)"
```

---

### Task 4: Frontend — "Run this page" on Signals

**Files:** Modify `client/src/pages/Signals.tsx` (+button → `runSurface("signals")`), reuse `runSurface` from the Industry plan; update `client/src/pages/signals.test.tsx`.

- [ ] **Step 1–3:** mirror the Industry Task 5 button pattern; assert the button posts `kind: "signals"`; `npm test` green.
- [ ] **Step 4: Commit** `feat(client): Run-this-page button on Signals (Signals)`.

---

## Self-Review

- **Spec coverage (§8, §11):** competitor set → Task 1; tiered structured→gate→search → Task 2; OSV fold-in as `security_advisory` structured source → Task 3; persistence + indexing → Task 3; Run-this-page → Task 4. ✓
- **Placeholder scan:** deps and tiering fully coded; `structured_for`/`persist_signals` specified with exact fields and the sub-type query templates. Task 1's count-fix note is a concrete action. ✓
- **Type consistency:** `SignalsDeps(targets, structured_fn, search_fn, gate_model)` and `(verdict, draft)`/`absent_draft` match the skeleton; `persist_signals(session, drafts)` consumes exactly the resolved-draft shape and skips `{"absent": True}`; `run_signals -> {...}` count feeds `_new_items_from_report`. Sub-type→signal_type mapping matches `signal_types.yaml`. ✓
