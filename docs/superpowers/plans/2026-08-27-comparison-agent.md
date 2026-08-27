# Comparison Agent: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A per-cell LangGraph agent that fills the 5×5 competitor grid — for each `(competitor, dimension)` it searches the competitor's product, rates strength against JFrog's position, writes a one-line capability summary with a source, and marks a cell `none` (no row) rather than fabricate.

**Architecture:** One `run_research` target per cell (5 competitors × 5 dimensions = 25). Search-first; `assess` returns `stance` + `summary` + `source_url` when a real capability is found, else `absent` (a legitimate `none` cell). Resolved cells upsert a `Claim` (subject = JFrog, asserting = competitor) carrying the new `stance` column, indexed for Ask. The grid read path is rewritten to read `stance` and the new 5-dimension taxonomy.

**Tech Stack:** Python 3.12, LangGraph, langchain-openai, SQLAlchemy, React, pytest, vitest.

**Spec:** [.../2026-08-27-per-surface-research-graphs-design.md](../specs/2026-08-27-per-surface-research-graphs-design.md) — §9.

## Global Constraints

- Prerequisite: **Foundation complete** and **Signals Task 1 complete** (the competitor set + `config/competitors.yaml`).
- Columns are the 5 buyer-facing dimensions, **not** `jfrog_components.yaml`. Registry-less rivals (Snyk/Aqua/Checkmarx) resolve to `none` for Artifact Management — that is correct.
- **No fabrication:** an unsubstantiated cell is `absent` → no `Claim` row → the grid renders `none`.
- `stance ∈ {strong, moderate, weak}` is only ever written for a *resolved* cell (with a source); `none` is the absence of a row.
- Suite green after each task: `pytest -q` (backend) and `npm test` (client).

## File map

**Created:** `config/comparison_dimensions.yaml`, `backend/agent/graphs/research/comparison/{__init__,deps}.py`, `backend/agent/prompts/research_comparison.md`, `backend/app/services/research/comparison_agent.py`, tests.
**Modified:** `backend/app/services/comparison_matrix.py` (read `stance` + new dims + allowlist), `backend/worker/jobs.py` (+`run_comparison`), `client/src/utils/comparisonPresentation.ts`, `client/src/components/ComparisonGrid.tsx`, `client/src/api/types.ts`, `client/src/pages/Comparison.tsx`, tests.
**Deleted:** `config/jfrog_components.yaml` (superseded).

---

### Task 1: The 5-dimension config (with JFrog yardsticks)

**Files:**
- Create: `config/comparison_dimensions.yaml`
- Test: `tests/test_comparison_dimensions.py`

- [ ] **Step 1: Failing test**

```python
# tests/test_comparison_dimensions.py
def test_five_dimensions_with_positions():
    from app.services.comparison_matrix import load_dimensions
    dims = load_dimensions()
    assert [d["key"] for d in dims] == [
        "artifact_management", "sca_sbom", "container_security",
        "cicd_integration", "developer_experience",
    ]
    assert all(d["jfrog_position"] for d in dims)          # every column has a yardstick
    assert all(d["probe_keywords"] for d in dims)
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Write `config/comparison_dimensions.yaml`** — the five dimensions from spec §9 with `key/label/probe_keywords/jfrog_position`. **The `cicd_integration` and `developer_experience` `jfrog_position` values are the drafts flagged NEEDS APPROVAL in the spec — use the approved text from the user before committing.**

- [ ] **Step 4: Implement `load_dimensions`** in `comparison_matrix.py`:
```python
def load_dimensions() -> list[dict]:
    from pathlib import Path
    import yaml
    from app.settings import settings
    return yaml.safe_load(
        (Path(settings.config_dir) / "comparison_dimensions.yaml").read_text(encoding="utf-8")
    )["dimensions"]
```

- [ ] **Step 5: Run → PASS. Commit.**

```bash
git add config/comparison_dimensions.yaml backend/app/services/comparison_matrix.py tests/test_comparison_dimensions.py
git commit -m "feat: 5-dimension comparison config with JFrog yardsticks (Comparison)"
```

---

### Task 2: Comparison deps — per-cell search + stance gate

**Files:**
- Create: `backend/agent/graphs/research/comparison/{__init__,deps}.py`, `backend/agent/prompts/research_comparison.md`
- Test: `tests/test_comparison_deps.py`

**Interfaces:**
- Produces: `ComparisonDeps(cells, search_fn, gate_model)` implementing `ResearchDeps`. `assess(target, hits, attempts) -> (verdict, draft)`; resolved draft `{"competitor","dimension","stance","summary","source_url"}` with `stance ∈ {strong,moderate,weak}`; `absent_draft(target) -> {"competitor","dimension","stance":"none"}`.

- [ ] **Step 1: Failing test**

```python
# tests/test_comparison_deps.py
from agent.graphs.research.comparison.deps import ComparisonDeps, CellVerdict
from agent.tools.web_search import SearchHit


def _cell(dim="artifact_management"):
    return {"competitor": "sonatype", "name": "Sonatype", "aliases": ["Nexus"],
            "dimension": dim, "label": "Artifact Management",
            "jfrog_reference": "Artifactory universal 30+ types"}


class StubGate:
    def __init__(self, found, stance="moderate"): self.found, self.stance = found, stance
    def invoke(self, _p):
        return CellVerdict(found=self.found, stance=self.stance,
                           summary="Nexus Repository, mature" if self.found else "",
                           source_url="https://x/nexus" if self.found else "")


def test_found_capability_resolves_with_stance():
    deps = ComparisonDeps([_cell()], search_fn=lambda t: [SearchHit("t", "https://x/nexus", "s")],
                          gate_model=StubGate(True, "moderate"))
    verdict, draft = deps.assess(_cell(), [SearchHit("t", "https://x/nexus", "s")], attempts=1)
    assert verdict == "resolved"
    assert draft["stance"] == "moderate" and draft["source_url"] == "https://x/nexus"


def test_no_capability_is_unresolved_then_absent_none():
    deps = ComparisonDeps([_cell()], search_fn=lambda t: [], gate_model=StubGate(False))
    verdict, draft = deps.assess(_cell(), [], attempts=1)
    assert verdict == "unresolved" and draft is None
    assert deps.absent_draft(_cell()) == {"competitor": "sonatype", "dimension": "artifact_management",
                                          "stance": "none"}
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `deps.py`**

```python
# backend/agent/graphs/research/comparison/deps.py
from __future__ import annotations

import json

from pydantic import BaseModel

from agent.llm import prompt as load_prompt
from agent.tools.web_search import web_search


class CellVerdict(BaseModel):
    found: bool
    stance: str      # strong | moderate | weak
    summary: str
    source_url: str


class ComparisonDeps:
    max_attempts = 3

    def __init__(self, cells, search_fn=None, gate_model=None):
        self._cells = cells
        self._gate = gate_model
        self._search = search_fn or (lambda t: web_search(self._query(t), k=5))

    def _query(self, target):
        product = " OR ".join([target["name"], *target["aliases"]])
        return f'({product}) {target["label"]} ({" OR ".join(target.get("probe_keywords", []))})'

    def plan(self):
        return list(self._cells)

    def collect(self, target):
        return None  # search-first

    def search(self, target):
        return self._search(target)

    def assess(self, target, hits, attempts):
        payload = {
            "competitor": target["name"], "aliases": target["aliases"],
            "dimension": target["label"], "jfrog_reference": target["jfrog_reference"],
            "hits": [{"title": h.title, "url": h.url, "snippet": h.snippet} for h in hits],
        }
        prompt_text = load_prompt("research_comparison") + "\n\nDATA:\n" + json.dumps(payload)
        v: CellVerdict = self._gate.invoke(prompt_text)
        if v.found and v.source_url and v.stance in {"strong", "moderate", "weak"}:
            return "resolved", {
                "competitor": target["competitor"], "dimension": target["dimension"],
                "stance": v.stance, "summary": v.summary, "source_url": v.source_url,
            }
        return "unresolved", None

    def absent_draft(self, target):
        return {"competitor": target["competitor"], "dimension": target["dimension"], "stance": "none"}
```

Create `__init__.py` (empty) and `research_comparison.md`: "You assess ONE competitor in ONE capability dimension against the JFrog reference. Only set found=true if you can point to a concrete, real capability with a source_url. Rate stance strong/moderate/weak versus the reference. If there is no public capability (e.g. the competitor has no product in this area), set found=false — never invent one."

- [ ] **Step 4: Run → PASS. Commit.**

```bash
git add backend/agent/graphs/research/comparison/ backend/agent/prompts/research_comparison.md tests/test_comparison_deps.py
git commit -m "feat: comparison per-cell stance gate deps (Comparison)"
```

---

### Task 3: App service — build cells, persist Claims, `run_comparison`

**Files:**
- Create: `backend/app/services/research/comparison_agent.py`
- Modify: `backend/worker/jobs.py`
- Test: `tests/test_comparison_agent.py`

**Interfaces:**
- Produces: `build_cells() -> list[dict]` (competitors × dimensions, with `jfrog_reference` from each dimension's `jfrog_position`); `persist_comparison(session, drafts) -> int`; `run_comparison() -> dict`.

- [ ] **Step 1: Failing test**

```python
# tests/test_comparison_agent.py
def test_build_cells_is_five_by_five():
    from app.services.research.comparison_agent import build_cells
    cells = build_cells()
    assert len(cells) == 25
    assert {c["competitor"] for c in cells} == {"github", "sonatype", "snyk", "aqua", "checkmarx"}


def test_persist_comparison_upserts_claim_with_stance_and_skips_none(session, monkeypatch):
    from app.models.registry import Entity
    from app.models.ledger import Claim
    from app.services.seeding import seed
    from app.services.research import comparison_agent, provenance
    seed(session)
    class FakeEmbedder:
        def embed(self, texts): return [[0.0]*1536 for _ in texts]
    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    drafts = [
        {"competitor": "sonatype", "dimension": "artifact_management", "stance": "moderate",
         "summary": "Nexus Repository", "source_url": "https://x/nexus"},
        {"competitor": "snyk", "dimension": "artifact_management", "stance": "none"},  # skipped
    ]
    n = comparison_agent.persist_comparison(session, drafts)
    session.flush()
    sonatype = session.query(Entity).filter_by(slug="sonatype").one()
    jfrog = session.query(Entity).filter_by(slug="jfrog").one()
    claim = session.query(Claim).filter_by(asserting_entity_id=sonatype.id,
                                           subject_entity_id=jfrog.id,
                                           dimension="artifact_management").one()
    assert n == 1 and claim.stance == "moderate" and claim.claim_text == "Nexus Repository"
    # idempotent: re-persisting updates the same row, not a duplicate
    comparison_agent.persist_comparison(session, drafts); session.flush()
    assert session.query(Claim).filter_by(asserting_entity_id=sonatype.id,
                                          dimension="artifact_management").count() == 1
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `comparison_agent.py`**

`build_cells()` = for competitor in `load_competitors()`, for dim in `load_dimensions()`: `{competitor, name, aliases, dimension: dim["key"], label: dim["label"], probe_keywords: dim["probe_keywords"], jfrog_reference: dim["jfrog_position"]}`. `persist_comparison` skips `stance == "none"`; for each resolved cell, `record_finding` + upsert `Claim(subject=jfrog, asserting=competitor, dimension, claim_text=summary, stance, claim_type="positioning", capability_tags=[dimension], reliability_grade="C", first_seen_at/last_confirmed_at=now)` (look up existing by `(asserting_entity_id, subject=jfrog, dimension)` and update in place) + `Evidence(quote=summary, quote_offset=0)` + `index_finding(record_type="claim", record_id=claim.id, ...)`. `run_comparison()` wires `ComparisonDeps(build_cells(), gate_model=get_model("gate").with_structured_output(CellVerdict, strict=True))`, runs, persists. Re-export `run_comparison` in `worker/jobs.py`.

- [ ] **Step 4: Run → PASS. Full suite. Commit.**

```bash
git add backend/app/services/research/comparison_agent.py backend/worker/jobs.py tests/test_comparison_agent.py
git commit -m "feat: comparison persist (Claim+stance) + run_comparison (Comparison)"
```

---

### Task 4: Rewrite the grid read path

**Files:**
- Modify: `backend/app/services/comparison_matrix.py`, `tests/test_comparison_matrix.py`
- Delete: `config/jfrog_components.yaml`

- [ ] **Step 1: Update `tests/test_comparison_matrix.py`** to expect: columns = the 5 dimension labels; rows = the 5 allowlisted competitors; a cell with a `Claim` returns its `stance` (strong/moderate/weak); a cell with no `Claim` returns `none`; `jfrog_position` from `comparison_dimensions.yaml`.

- [ ] **Step 2: Rewrite `build_comparison_matrix`** to iterate `load_dimensions()` for columns and `load_competitors()` for rows; for each cell look up `Claim` by `(asserting_entity_id=competitor, subject=jfrog, dimension=dim.key)`; set cell `stance = claim.stance if claim else "none"`, `summary = claim.claim_text if claim else "No public claim on record."`, `jfrog_position = dim["jfrog_position"]`, `evidence = evidence_for_claim(session, claim)`. Remove `_load_components`, `_claim_for_component`, and the `jfrog_components.yaml` read.

- [ ] **Step 3: `git rm config/jfrog_components.yaml`** and grep to confirm no other importer:
Run: `grep -rn "jfrog_components" backend tests --include=*.py` → expect none after the rewrite.

- [ ] **Step 4: Run → PASS. Commit.**

```bash
git add backend/app/services/comparison_matrix.py tests/test_comparison_matrix.py config/jfrog_components.yaml
git commit -m "refactor: comparison grid reads stance + 5-dim taxonomy (Comparison)"
```

---

### Task 5: Frontend — 5 columns, strength from `stance`

**Files:**
- Modify: `client/src/utils/comparisonPresentation.ts`, `client/src/components/ComparisonGrid.tsx`, `client/src/api/types.ts`
- Test: `client/src/pages/comparison.test.tsx`, `client/src/pages/grids.test.tsx`

- [ ] **Step 1: Update `api/types.ts`** — cell `stance` is now `"strong" | "moderate" | "weak" | "none"` (drop the ahead/comparable/behind vocabulary).
- [ ] **Step 2: Simplify `comparisonPresentation.ts`** — `stance` already IS the strength; replace `stanceToStrength` with an identity/label map and update `DIMENSION_LABELS` to the 5 dimension keys (`artifact_management`, `sca_sbom`, `container_security`, `cicd_integration`, `developer_experience`). Update `deriveThreat`/`buildCompetitorSummary` to count on the new stance values.
- [ ] **Step 3: Update `ComparisonGrid.tsx`** to render columns from the 5 dimensions and the strength dot from `stance`.
- [ ] **Step 4: Update the tests** to the new competitor rows + 5 columns + stance values. Run `npm test` → PASS.
- [ ] **Step 5: Commit** `feat(client): comparison grid on 5 dimensions + stance strength (Comparison)`.

---

### Task 6: Frontend — "Run this page" on Comparison

**Files:** Modify `client/src/pages/Comparison.tsx` (+button → `runSurface("comparison")`); update `client/src/pages/comparison.test.tsx`.

- [ ] **Step 1–3:** mirror the Industry Task 5 pattern; assert the button posts `kind: "comparison"`; `npm test` green.
- [ ] **Step 4: Commit** `feat(client): Run-this-page button on Comparison (Comparison)`.

---

## Self-Review

- **Spec coverage (§9):** 5 dimensions + yardsticks → Task 1; per-cell search + stance gate + no-fabrication `none` → Task 2; 25 cells + Claim upsert with `stance` + indexing → Task 3; grid read path on `stance`/new taxonomy → Task 4; frontend columns + strength → Task 5; Run-this-page → Task 6. Competitor set consumed from Signals Task 1 (prerequisite). ✓
- **Placeholder scan:** deps, persistence, and read-path rewrite are fully specified; the one genuine open value (`jfrog_position` for the two new dimensions) is called out in Task 1 Step 3 as requiring the user's approved text before commit — not a silent placeholder. ✓
- **Type consistency:** `ComparisonDeps` `(verdict, draft)` / `absent_draft(stance="none")` match the skeleton; `persist_comparison(session, drafts)` consumes the resolved-draft shape and skips `stance=="none"`; `Claim.stance` (Foundation Task 1) is written here and read in Task 4; frontend `stance` union (Task 5) matches the backend cell field from Task 4. ✓
