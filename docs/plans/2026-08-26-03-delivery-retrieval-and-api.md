# Delivery, Retrieval & API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This plan may also be executed in **fast mode** — build all tasks, then run the suite once at the end — using the same rules as Plan 2's fast-mode prompt.

> ## ⛔ Precondition — Plan 2 must be complete
>
> ```bash
> docker compose run --rm api pytest -v        # entire suite green
> curl http://localhost:8000/stats             # signals > 0, captures >= 10, claim_versions > 0
> curl http://localhost:8000/runs/status       # reports next_run_at
> grep -rE "openai|langchain|langgraph" backend/app/   # returns NOTHING
> ```
>
> If any check fails, stop and report. Do not repair Plan 2 from inside this plan.

**Goal:** Everything the analyst actually sees — a derived comparison view, computed trends, a grounded Ask surface, per-persona digests delivered by email, and the 21 endpoints the client consumes.

**Architecture:** Plans 1–2 built layers 1–6 (Collect → Score). Plan 3 builds layer 7 (Deliver) plus the retrieval stack that the Ask surface and cross-reference need. It also closes the fifteen gaps the API-contract review found between the mockup and the pipeline.

**Tech Stack:** Everything from Plans 1–2, plus pgvector 0.5 · Jinja2 3.1 · css-inline 0.21

**Spec:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §6–8 (ingestion, indexing, retrieval), §9 (digest assembly) · [`docs/DESIGN.md`](../DESIGN.md) §6 (retrieval boundary) · [`docs/PRD.md`](../PRD.md) §5.5, §5.5b, §5.6, §5.7 · [`docs/API_CONTRACT.md`](../API_CONTRACT.md) — **the endpoint shapes are already specified and verified against the mockup; match them exactly**

## Global Constraints

All Plan 1 and Plan 2 constraints remain in force. Additionally:

- **The client fixtures in `client/src/fixtures/*.json` are the contract's ground truth.** Every endpoint must return a shape that validates against its fixture. If an endpoint cannot, the gap is real — report it rather than changing the fixture.
- **`app/` still never imports `langchain`/`langgraph`/`openai`.** The Ask graph lives in `agent/graphs/ask/`, reached only through `agent_service`.
- **The retrieval service lives in `app/services/retrieval/`, not in `agent/`.** It is deterministic SQL and must be unit-testable with no model. The Ask agent reaches it through a port.
- **The daily brief performs no retrieval.** Digest assembly reads structured `Signal` rows directly. The vector store exists and the brief deliberately does not call it.
- **No test makes a real API call** — neither OpenAI nor SMTP. Both clients are faked.

**Dependencies to add:**

```toml
"pgvector>=0.5,<0.6",
"jinja2>=3.1,<4",
"css-inline>=0.21,<0.22",
```

## Cut order — Day 3 is over-subscribed, decide now

Tasks are marked **[MUST]** or **[CUT-n]**. If time runs short, drop in ascending cut order and document what was cut in the README. Never cut a **[MUST]**.

| Cut | Task | What is lost |
|---|---|---|
| CUT-1 | 12 — write endpoints beyond analyst actions | Settings becomes read-only; config edited via YAML + reseed |
| CUT-2 | 5, 6, 7 — chunking, embedding, retrieval | Ask falls back to structured-record stuffing over recent signals only |
| CUT-3 | 8 — Ask graph | The Ask screen is cut entirely; it is the most commoditised surface |
| CUT-4 | 10 — SMTP send | Digest renders in-app; one manual send proves the path |
| CUT-5 | 2 — trend aggregation | Exec view falls back to top clustered themes by volume |

---

## File Structure

| File | Responsibility |
|---|---|
| `config/jfrog_positions.yaml` | JFrog's own position per capability dimension — **analyst-authored** |
| `config/trends.yaml` | Trend window, thresholds, minimum signal counts |
| `config/retrieval.yaml` | RRF, rerank boosts, diversity, expansion, `hnsw_ef_search` |
| `config/delivery.yaml` | SMTP settings, digest send times, recipient lists |
| `backend/app/models/delivery.py` | `Chunk`, `UserVisit`, `DigestRun`, `Delivery` |
| `backend/app/services/trends.py` | Signals over time → `Trend` |
| `backend/app/services/comparison.py` | Claims + JFrog positions → `ComparisonRow` |
| `backend/app/services/coverage.py` | entities × signal types → coverage matrix |
| `backend/app/services/ingestion/chunking.py` | Elements → chunks under a token budget |
| `backend/app/services/ingestion/embedding.py` | Chunks → vectors, idempotent upsert |
| `backend/app/services/retrieval/query.py` | Hybrid RRF + domain rerank |
| `backend/app/services/delivery/assembly.py` | Digest selection under budget |
| `backend/app/services/delivery/email.py` | Jinja render, CSS inline, SMTP |
| `backend/app/services/delivery/templates/digest.html.j2` | The one persona-parameterised template |
| `backend/agent/graphs/ask/` | Intent → bounded tool loop → grounding gate → answer \| refuse |
| `backend/app/routers/*.py` | The 21 endpoints |

### Interfaces established by this plan

```python
# services/trends.py
@dataclass(frozen=True)
class Trend:
    theme: str
    direction: Literal["rising", "falling", "steady"]
    velocity: Literal["emerging", "accelerating", "steady", "decaying"]
    signal_count: int
    distinct_sources: int
    confidence: Literal["low", "medium", "high"]
    window_start: date
    window_end: date
    contributing_signal_ids: list[int]

def compute_trends(signals: list[dict], cfg: TrendConfig, as_of: date) -> list[Trend]: ...

# services/comparison.py
@dataclass(frozen=True)
class ComparisonCell:
    text: str | None
    grade: str | None          # None when authored or absent — see G6/G7
    origin: Literal["extracted", "authored", "absent"]
    evidence_id: int | None

@dataclass(frozen=True)
class ComparisonRow:
    dimension: str
    jfrog: ComparisonCell
    competitor: ComparisonCell
    last_changed_at: datetime | None

def build_comparison(session, competitor_slug: str, cfg) -> list[ComparisonRow]: ...

# services/ingestion/chunking.py
@dataclass(frozen=True)
class Chunk:
    text: str; prefix: str; section_path: tuple[str, ...]
    element_orders: tuple[int, ...]; token_count: int

def chunk_elements(elements: list[Element], cfg: ChunkingConfig) -> list[Chunk]: ...

# services/retrieval/query.py
@dataclass(frozen=True)
class Hit:
    chunk_id: int; record_type: str; record_id: int
    text: str; score: float; source_id: int; reliability_grade: str

def search(session, *, query: str, preset: str, filters: dict, cfg) -> list[Hit]: ...

# services/delivery/assembly.py
@dataclass(frozen=True)
class Digest:
    persona: str; items: list[dict]; interrupts: list[dict]
    silent_entities: list[str]; generated_at: datetime

def assemble(session, persona: str, cfg, as_of: datetime) -> Digest: ...
```

---

### Task 1 [MUST]: Gap fixes and configuration

**Closes G5, G6, G9, G12, G15 from the API contract review.**

**Files:**
- Create: `config/jfrog_positions.yaml`, `config/trends.yaml`, `config/delivery.yaml`, `backend/app/models/delivery.py`
- Modify: `config/entities.yaml` (fifth competitor), `config/signal_types.yaml` (coverage columns), `backend/app/config/schema.py`, `backend/app/services/collection/fetcher.py` — **one additive behaviour**: increment a check counter
- Test: `tests/test_gap_fixes.py`

**Interfaces:**
- Produces: `UserVisit`, `Chunk`, `DigestRun`, `Delivery` models; `AppConfig.jfrog_positions`, `.trends`, `.delivery`; `Source.check_count`

- [ ] **Step 1: Write the failing test**

```python
from app.config.loader import load_config

def test_jfrog_positions_cover_every_comparison_dimension():
    config = load_config()
    dimensions = {p.dimension for p in config.jfrog_positions.positions}
    assert "malware_detection" in dimensions
    assert len(dimensions) >= 6

def test_jfrog_positions_are_marked_authored_not_extracted():
    """JFrog's own positioning is authored by the CI team, not discovered.
    It must never be presented as graded evidence."""
    for position in load_config().jfrog_positions.positions:
        assert position.origin == "authored"
        assert not hasattr(position, "reliability_grade")

def test_coverage_columns_match_the_signal_type_enum():
    config = load_config()
    assert set(config.signal_types.coverage_columns) == set(config.signal_types.types)

def test_a_fifth_competitor_is_configured():
    slugs = {e.slug for e in load_config().entities if e.kind == "competitor"}
    assert len(slugs) >= 5

def test_check_counter_increments_even_on_304(session, seeded_source, not_modified_fetcher):
    from app.services.collection.recording import record_check
    before = seeded_source.check_count
    record_check(session, seeded_source, status=304)
    assert seeded_source.check_count == before + 1

def test_user_visit_records_last_seen(session):
    from app.models.delivery import UserVisit
    from datetime import UTC, datetime
    visit = UserVisit(actor="analyst@jfrog.com", last_seen_at=datetime.now(UTC))
    session.add(visit); session.flush()
    assert visit.last_seen_at is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose run --rm api pytest tests/test_gap_fixes.py -v`
Expected: FAIL — `AttributeError: 'AppConfig' object has no attribute 'jfrog_positions'`

- [ ] **Step 3: Write `config/jfrog_positions.yaml`**

```yaml
# JFrog's own position per comparison dimension.
#
# This file is AUTHORED by the Competitive Intelligence team, not extracted
# from a source. Competitor cells in the comparison view carry an Admiralty
# grade because they were extracted from a graded source and verified against
# a stored capture. These cells cannot and must not — there is no capture to
# verify them against. The interface marks them "authored" for exactly that
# reason. Presenting authored text as graded evidence would be the same
# category of unfounded confidence the system exists to prevent.
positions:
  - dimension: malware_detection
    origin: authored
    text: "Curation blocks malicious packages at the gate; Xray adds contextual analysis to determine applicability."
  - dimension: sbom
    origin: authored
    text: "AppTrust provides SBOM generation, management and evidence collection across the release lifecycle."
  - dimension: pricing_model
    origin: authored
    text: "Subscription tiers by capability; enterprise pricing is quoted."
  - dimension: package_format_support
    origin: authored
    text: "Universal binary repository — 30+ package types under one system of record."
  - dimension: model_registry
    origin: authored
    text: "AI Catalog and JFrog ML provide model and MCP-artifact management alongside binaries."
  - dimension: runtime_security
    origin: authored
    text: "Runtime Security correlates deployed workloads back to build and package provenance."
  - dimension: deployment_model
    origin: authored
    text: "Self-hosted, SaaS, hybrid and air-gapped."
```

- [ ] **Step 4: Write `config/trends.yaml` and `config/delivery.yaml`**

```yaml
# config/trends.yaml
window_weeks: 4
comparison_windows: 2          # current window vs the preceding one
min_signals_for_trend: 3
direction:
  rising_ratio: 1.35           # current / prior above this = rising
  falling_ratio: 0.70
velocity:
  emerging_prior_max: 1        # near-zero prior volume = emerging
  accelerating_ratio: 1.80
confidence:
  high: { min_signals: 8, min_sources: 3 }
  medium: { min_signals: 4, min_sources: 2 }
```

```yaml
# config/delivery.yaml
smtp:
  host: smtp.gmail.com
  port: 587
  starttls: true
  from_name: JFrog Competitive Intelligence
send_at:
  sales:   "07:00"
  product: "07:00"
  exec:    "FRI 08:00"
recipients:
  sales:   []
  product: []
  exec:    []
app_base_url: http://localhost:5173
```

- [ ] **Step 5: Add `check_count` and the recording helper**

Add to `Source`: `check_count: Mapped[int] = mapped_column(Integer, default=0)` and
`last_checked_at: Mapped[datetime | None]`.

```python
# app/services/collection/recording.py
from datetime import UTC, datetime
from sqlalchemy.orm import Session
from app.models.registry import Source

def record_check(session: Session, source: Source, status: int) -> None:
    """A check is a fetch attempt, including a 304. Captures are not checks —
    conditional GET means an unchanged page produces no capture, so counting
    captures would understate how often we looked."""
    source.check_count = (source.check_count or 0) + 1
    source.last_checked_at = datetime.now(UTC)
    session.flush()
```

Call it from the collection job for every fetch, whatever the status.

- [ ] **Step 6: Add the models to `backend/app/models/delivery.py`**

`UserVisit` (actor, last_seen_at), `DigestRun` (persona, generated_at, item_count),
`Delivery` (digest_run_id, recipient, sent_at, status), and `Chunk` — defined here but its
vector column is added in Task 6.

- [ ] **Step 7: Add the fifth competitor and reconcile coverage columns**

`config/entities.yaml` — append:

```yaml
  - { slug: azure_artifacts, name: Azure Artifacts, kind: competitor, tier: 2, aliases: ["Azure DevOps Artifacts"] }
```

`config/signal_types.yaml` — add `coverage_columns:` listing **all nine** types. The mockup
showed eight; nine is correct.

- [ ] **Step 8: Run tests, then the full suite**

Run: `docker compose run --rm api pytest tests/test_gap_fixes.py -v && docker compose run --rm api pytest -v`
Expected: new tests PASS; Plans 1–2 still PASS

- [ ] **Step 9: Commit**

```bash
git add config backend/app/models/delivery.py backend/app/services/collection/recording.py backend/app/config tests/test_gap_fixes.py
git commit -m "feat: close contract gaps — authored JFrog positions, check counter, last-seen, coverage enum"
```

---

### Task 2 [CUT-5]: Trend aggregation

**Closes G1, G2, G3 — the executive view as mocked was not producible.**

**Files:**
- Create: `backend/app/services/trends.py`
- Test: `tests/test_trends.py`

**Interfaces:**
- Produces: `Trend`, `compute_trends(signals, cfg, as_of)`

**Why deterministic:** direction and velocity computed from clustered signal volume are
reproducible, explainable and tunable. A model asked to "identify trends" produces different
answers on each run, which makes the executive view unfalsifiable — the one audience least
tolerant of that.

- [ ] **Step 1: Write the failing test**

```python
from datetime import UTC, date, datetime, timedelta
from app.config.loader import load_config
from app.services.trends import compute_trends

CFG = load_config().trends
AS_OF = date(2026, 8, 26)

def sig(theme, weeks_ago, source_id=1, signal_id=None):
    return {"id": signal_id or (weeks_ago * 100 + source_id),
            "capability_tags": [theme], "source_id": source_id,
            "occurred_at": datetime.now(UTC) - timedelta(weeks=weeks_ago)}

def test_growing_volume_reads_as_rising():
    signals = ([sig("model_registry", 1, s) for s in range(1, 7)] +
               [sig("model_registry", 6, s) for s in range(1, 3)])
    trend = next(t for t in compute_trends(signals, CFG, AS_OF) if t.theme == "model_registry")
    assert trend.direction == "rising"

def test_near_zero_prior_volume_reads_as_emerging():
    signals = [sig("model_registry", 1, s) for s in range(1, 6)]
    trend = next(t for t in compute_trends(signals, CFG, AS_OF) if t.theme == "model_registry")
    assert trend.velocity == "emerging"

def test_a_theme_below_the_minimum_produces_no_trend():
    signals = [sig("sbom", 1)]
    assert [t for t in compute_trends(signals, CFG, AS_OF) if t.theme == "sbom"] == []

def test_confidence_requires_independent_sources_not_just_volume():
    """Ten signals from one source is not corroboration."""
    same_source = [sig("sbom", 1, source_id=1, signal_id=i) for i in range(10)]
    many_sources = [sig("sbom", 1, source_id=s, signal_id=100 + s) for s in range(1, 11)]
    assert compute_trends(same_source, CFG, AS_OF)[0].confidence != "high"
    assert compute_trends(many_sources, CFG, AS_OF)[0].confidence == "high"

def test_every_trend_lists_the_signals_that_produced_it():
    signals = [sig("sbom", 1, s) for s in range(1, 6)]
    trend = compute_trends(signals, CFG, AS_OF)[0]
    assert len(trend.contributing_signal_ids) == 5
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose run --rm api pytest tests/test_trends.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.trends'`

- [ ] **Step 3: Implement `trends.py`**

```python
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from app.config.schema import TrendConfig

@dataclass(frozen=True)
class Trend:
    theme: str
    direction: Literal["rising", "falling", "steady"]
    velocity: Literal["emerging", "accelerating", "steady", "decaying"]
    signal_count: int
    distinct_sources: int
    confidence: Literal["low", "medium", "high"]
    window_start: date
    window_end: date
    contributing_signal_ids: list[int]

def _confidence(count: int, sources: int, cfg: TrendConfig) -> str:
    if count >= cfg.confidence["high"]["min_signals"] and sources >= cfg.confidence["high"]["min_sources"]:
        return "high"
    if count >= cfg.confidence["medium"]["min_signals"] and sources >= cfg.confidence["medium"]["min_sources"]:
        return "medium"
    return "low"

def compute_trends(signals: list[dict], cfg: TrendConfig, as_of: date) -> list[Trend]:
    """Deterministic aggregation over clustered signal volume.

    Current window vs the preceding window of equal length. Direction is the
    ratio; velocity distinguishes a theme appearing from nothing (emerging)
    from one already present and speeding up (accelerating).
    """
    now = datetime.now(UTC)
    window = timedelta(weeks=cfg.window_weeks)
    current_start, prior_start = now - window, now - (window * 2)

    current: dict[str, list[dict]] = defaultdict(list)
    prior: dict[str, list[dict]] = defaultdict(list)
    for signal in signals:
        occurred = signal["occurred_at"]
        bucket = current if occurred >= current_start else (prior if occurred >= prior_start else None)
        if bucket is None:
            continue
        for theme in signal.get("capability_tags") or ["_untagged"]:
            bucket[theme].append(signal)

    trends: list[Trend] = []
    for theme, items in current.items():
        if len(items) < cfg.min_signals_for_trend:
            continue
        prior_count = len(prior.get(theme, []))
        ratio = len(items) / prior_count if prior_count else float("inf")

        if ratio >= cfg.direction["rising_ratio"]:
            direction = "rising"
        elif ratio <= cfg.direction["falling_ratio"]:
            direction = "falling"
        else:
            direction = "steady"

        if prior_count <= cfg.velocity["emerging_prior_max"]:
            velocity = "emerging"
        elif ratio >= cfg.velocity["accelerating_ratio"]:
            velocity = "accelerating"
        elif direction == "falling":
            velocity = "decaying"
        else:
            velocity = "steady"

        sources = {s["source_id"] for s in items}
        trends.append(Trend(
            theme=theme, direction=direction, velocity=velocity,
            signal_count=len(items), distinct_sources=len(sources),
            confidence=_confidence(len(items), len(sources), cfg),
            window_start=(now - window).date(), window_end=as_of,
            contributing_signal_ids=[s["id"] for s in items],
        ))

    return sorted(trends, key=lambda t: (-t.signal_count, t.theme))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm api pytest tests/test_trends.py -v`
Expected: PASS (all five)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/trends.py config/trends.yaml tests/test_trends.py
git commit -m "feat: deterministic trend aggregation for the executive view"
```

---

### Task 3 [MUST]: Comparison view derivation

**Closes G6 and G7.** Implements R5.1–R5.4.

**Files:**
- Create: `backend/app/services/comparison.py`
- Test: `tests/test_comparison.py`

**Interfaces:**
- Consumes: `Claim`, `ClaimVersion`, `Evidence`, `config.jfrog_positions`
- Produces: `ComparisonCell`, `ComparisonRow`, `build_comparison(session, competitor_slug, cfg)`

- [ ] **Step 1: Write the failing test**

```python
from app.services.comparison import build_comparison

def test_competitor_cells_carry_a_grade_and_evidence(session, seeded_claims):
    rows = build_comparison(session, "sonatype", cfg=...)
    row = next(r for r in rows if r.dimension == "malware_detection")
    assert row.competitor.origin == "extracted"
    assert row.competitor.grade is not None
    assert row.competitor.evidence_id is not None

def test_jfrog_cells_are_authored_and_carry_no_grade(session, seeded_claims):
    """There is no capture to verify authored text against. Grading it would be
    the same unfounded confidence the system exists to prevent."""
    row = build_comparison(session, "sonatype", cfg=...)[0]
    assert row.jfrog.origin == "authored"
    assert row.jfrog.grade is None

def test_a_dimension_with_no_competitor_claim_is_absent_not_graded(session, seeded_claims):
    """G7: the pipeline records what a source says, not that a claim is absent."""
    rows = build_comparison(session, "sonatype", cfg=...)
    row = next(r for r in rows if r.dimension == "runtime_security")
    assert row.competitor.origin == "absent"
    assert row.competitor.grade is None
    assert row.competitor.text is None

def test_recently_changed_rows_expose_their_change_time(session, seeded_claims_with_history):
    rows = build_comparison(session, "sonatype", cfg=...)
    changed = [r for r in rows if r.last_changed_at is not None]
    assert changed

def test_every_dimension_in_config_appears_even_with_no_claims(session):
    rows = build_comparison(session, "harbor", cfg=...)
    assert len(rows) >= 6
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose run --rm api pytest tests/test_comparison.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.comparison'`

- [ ] **Step 3: Implement `comparison.py`**

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entity_helpers import entity_by_slug     # small helper; add if absent
from app.models.ledger import Claim, ClaimVersion, Evidence

@dataclass(frozen=True)
class ComparisonCell:
    text: str | None
    grade: str | None
    origin: Literal["extracted", "authored", "absent"]
    evidence_id: int | None

@dataclass(frozen=True)
class ComparisonRow:
    dimension: str
    jfrog: ComparisonCell
    competitor: ComparisonCell
    last_changed_at: datetime | None

def build_comparison(session: Session, competitor_slug: str, cfg) -> list[ComparisonRow]:
    """Rows are derived, never authored — except JFrog's own column, which is
    authored by definition and marked as such."""
    competitor = entity_by_slug(session, competitor_slug)
    authored = {p.dimension: p.text for p in cfg.jfrog_positions.positions}

    claims = session.execute(
        select(Claim).where(Claim.asserting_entity_id == competitor.id)
    ).scalars().all()
    by_dimension = {c.dimension: c for c in claims if c.dimension}

    rows: list[ComparisonRow] = []
    for dimension, jfrog_text in authored.items():
        claim = by_dimension.get(dimension)

        if claim is None:
            competitor_cell = ComparisonCell(None, None, "absent", None)
            last_changed = None
        else:
            evidence = session.execute(
                select(Evidence).where(Evidence.claim_id == claim.id).limit(1)
            ).scalar_one_or_none()
            competitor_cell = ComparisonCell(
                text=claim.claim_text, grade=claim.reliability_grade,
                origin="extracted", evidence_id=evidence.id if evidence else None,
            )
            last_changed = session.execute(
                select(ClaimVersion.changed_at)
                .where(ClaimVersion.claim_id == claim.id)
                .order_by(ClaimVersion.changed_at.desc()).limit(1)
            ).scalar_one_or_none()

        rows.append(ComparisonRow(
            dimension=dimension,
            jfrog=ComparisonCell(jfrog_text, None, "authored", None),
            competitor=competitor_cell,
            last_changed_at=last_changed,
        ))
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose run --rm api pytest tests/test_comparison.py -v`
Expected: PASS (all five)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/comparison.py tests/test_comparison.py
git commit -m "feat: comparison view — extracted, authored and absent cells distinguished"
```

---

### Task 4 [MUST]: Collection coverage matrix

Implements R5.5 — the control against collection bias.

**Files:**
- Create: `backend/app/services/coverage.py`
- Test: `tests/test_coverage.py`

- [ ] **Step 1: Write the failing test**

```python
from app.services.coverage import build_coverage_matrix

def test_matrix_has_a_row_per_entity_and_a_column_per_signal_type(session, seeded_sources):
    matrix = build_coverage_matrix(session, cfg=...)
    assert len(matrix.columns) == 9
    assert any(row.entity == "sonatype" for row in matrix.rows)

def test_a_cell_with_no_source_is_reported_as_a_gap(session, seeded_sources):
    matrix = build_coverage_matrix(session, cfg=...)
    row = next(r for r in matrix.rows if r.entity == "harbor")
    assert row.cells["pricing_packaging"].source_count == 0
    assert row.cells["pricing_packaging"].status == "gap"

def test_disabled_and_robots_blocked_sources_do_not_count_as_coverage(session, blocked_source):
    matrix = build_coverage_matrix(session, cfg=...)
    row = next(r for r in matrix.rows if r.entity == blocked_source.entity_slug)
    assert row.cells[blocked_source.covers].source_count == 0

def test_gap_total_is_reported_for_the_settings_header(session, seeded_sources):
    assert build_coverage_matrix(session, cfg=...).gap_count > 0
```

- [ ] **Step 2–4: Run, implement, run**

Implement a `CoverageMatrix` dataclass with `columns: list[str]`, `rows: list[CoverageRow]`
and `gap_count: int`. A source contributes to a cell when it is enabled, `robots_allowed` is
not `False`, and its configured `covers` list includes that signal type. Add
`covers: list[str]` to `SourceConfig` and the `Source` model, defaulting to all types for
`html_page` sources and to the adapter's hint for `api` sources.

Run: `docker compose run --rm api pytest tests/test_coverage.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: collection coverage matrix — collection gap analysis"
```

---

### Task 5 [CUT-2]: Chunking service

**Files:**
- Create: `backend/app/services/ingestion/chunking.py`
- Test: `tests/test_chunking.py`

**Interfaces:**
- Consumes: `Element`, `ElementKind` (Plan 1), `ChunkingConfig` (Plan 1 Task 2)
- Produces: `Chunk`, `chunk_elements(elements, cfg)`

- [ ] **Step 1: Write the failing test**

```python
from app.config.loader import load_config
from app.services.normalization.elements import Element, ElementKind
from app.services.ingestion.chunking import chunk_elements

CFG = load_config().chunking

def row(text, order, path=("Comparison",)):
    return Element(ElementKind.table_row, text, order, path=path,
                   attrs={"cells": text.split(" | ")})

def test_a_table_row_is_never_split():
    long_row = row("Malware detection | " + ("x " * 2000) + "| Limited", 0)
    chunks = chunk_elements([long_row], CFG)
    assert len(chunks) == 1                      # oversized, but intact

def test_chunks_do_not_merge_across_a_heading_of_the_configured_level():
    elements = [
        Element(ElementKind.heading, "Security", 0, level=2),
        Element(ElementKind.paragraph, "a " * 50, 1, path=("Security",)),
        Element(ElementKind.heading, "Pricing", 2, level=2),
        Element(ElementKind.paragraph, "b " * 50, 3, path=("Pricing",)),
    ]
    chunks = chunk_elements(elements, CFG)
    assert len(chunks) == 2

def test_every_chunk_carries_a_context_prefix_with_its_section_path():
    chunks = chunk_elements([row("Malware detection | Fully identifies | Limited", 0)], CFG)
    assert "Comparison" in chunks[0].prefix

def test_consecutive_short_elements_group_under_the_budget():
    elements = [Element(ElementKind.paragraph, "short text here", i, path=("S",)) for i in range(5)]
    assert len(chunk_elements(elements, CFG)) == 1
```

- [ ] **Step 2–4: Run, implement, run**

Group consecutive elements while the running token count (via `tiktoken`) stays under
`target_tokens`; never merge across a heading at or above `break_on_heading_level`; never
split an element whose kind is in `never_split`; fall back to recursive splitting only for a
single paragraph exceeding `max_tokens`. The prefix is
`[{source_name} · {section_path joined} · {captured_at}]`.

Run: `docker compose run --rm api pytest tests/test_chunking.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: element-grouping chunker with context prefixes"
```

---

### Task 6 [CUT-2]: Embedding and pgvector indexing

**Files:**
- Create: `backend/app/services/ingestion/embedding.py`, `backend/alembic/versions/0003_chunks_vector.py`
- Modify: `backend/app/models/delivery.py` (`Chunk` gains its vector and tsvector columns)
- Test: `tests/test_embedding.py`

- [ ] **Step 1: Write the failing test**

```python
def test_upsert_is_idempotent_on_identical_content(session, fake_embedder):
    from app.services.ingestion.embedding import index_chunks
    chunks = [...]
    index_chunks(session, chunks, record_type="claim", record_id=1, embedder=fake_embedder)
    first = session.query(Chunk).count()
    index_chunks(session, chunks, record_type="claim", record_id=1, embedder=fake_embedder)
    assert session.query(Chunk).count() == first
    assert fake_embedder.calls == 1          # not re-embedded

def test_changing_the_embed_model_marks_existing_chunks_stale(session, fake_embedder):
    from app.services.ingestion.embedding import stale_chunk_count
    ...
    assert stale_chunk_count(session, current_model="text-embedding-3-large") > 0

def test_chunk_metadata_is_stored_as_columns_not_json(session):
    """Metadata is filtered in SQL before the vector search; JSONB will not use btree."""
    from app.models.delivery import Chunk
    for column in ("entity_id", "signal_type", "published_at", "reliability_grade"):
        assert column in Chunk.__table__.columns
```

- [ ] **Step 2: Write the migration with the HNSW index in raw SQL**

```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        ALTER TABLE chunk
          ADD COLUMN embedding vector(1536),
          ADD COLUMN tsv tsvector
            GENERATED ALWAYS AS (to_tsvector('english', coalesce(prefix,'') || ' ' || text)) STORED
    """)
    op.execute("""
        CREATE INDEX chunk_embedding_hnsw ON chunk
        USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
    """)
    op.execute("CREATE INDEX chunk_tsv_gin ON chunk USING gin (tsv)")
```

- [ ] **Step 3–5: Implement, run, commit**

Upsert key: `(record_type, record_id, content_hash, embed_model, embed_version)`. The
embedder is injected so tests never call OpenAI.

Run: `docker compose run --rm api pytest tests/test_embedding.py -v` → PASS

```bash
git commit -am "feat: pgvector chunk index with HNSW and generated tsvector"
```

---

### Task 7 [CUT-2]: Hybrid retrieval

**Files:**
- Create: `backend/app/services/retrieval/query.py`, `backend/app/services/retrieval/rerank.py`
- Test: `tests/test_retrieval.py`

- [ ] **Step 1: Write the failing test**

```python
def test_the_prefilter_is_mandatory_and_narrows_before_similarity(session, indexed_chunks):
    from app.services.retrieval.query import search
    hits = search(session, query="malware", preset="ask_ledger",
                  filters={"entity_ids": [SONATYPE_ID]}, cfg=...)
    assert all(h.source_id in SONATYPE_SOURCE_IDS for h in hits)

def test_rrf_fuses_lexical_and_semantic_without_scale_tuning(session, indexed_chunks):
    hits = search(session, query="cargo registry", preset="ask_ledger", filters={}, cfg=...)
    assert hits and hits[0].score > hits[-1].score

def test_a_primary_grade_a_source_outranks_a_more_similar_blog(session, indexed_chunks):
    """The rerank encodes evidentiary value, not topical relevance."""
    hits = search(session, query="pricing", preset="ask_ledger", filters={}, cfg=...)
    assert hits[0].reliability_grade == "A"

def test_no_more_than_the_configured_chunks_come_from_one_document(session, indexed_chunks):
    hits = search(session, query="registry", preset="ask_ledger", filters={}, cfg=...)
    from collections import Counter
    assert max(Counter(h.record_id for h in hits).values()) <= 2

def test_an_empty_prefilter_returns_nothing_and_never_widens(session, indexed_chunks):
    """A retriever that relaxes its own filter is how ungrounded answers happen."""
    hits = search(session, query="anything", preset="ask_ledger",
                  filters={"entity_ids": [999999]}, cfg=...)
    assert hits == []
```

- [ ] **Step 2–4: Run, implement the SQL from ARCHITECTURE §8, run**

Run: `docker compose run --rm api pytest tests/test_retrieval.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: hybrid RRF retrieval with evidentiary rerank"
```

---

### Task 8 [CUT-3]: The Ask graph

**Files:**
- Create: `backend/agent/graphs/ask/state.py`, `graph.py`, `backend/agent/tools/ledger.py`, `backend/agent/prompts/ask.md`
- Test: `tests/test_ask_graph.py`

**Interfaces:**
- Produces: `build_ask_graph(deps)`, `AskResult(answer, citations, refused, reason)`

- [ ] **Step 1: Write the failing test**

```python
def test_a_supported_question_is_answered_with_citations(ask_deps):
    graph = build_ask_graph(ask_deps(hits=[HIT_A, HIT_B]))
    result = graph.invoke({"question": "What does Sonatype claim about JFrog pricing?"},
                          config={"configurable": {"thread_id": "a1"}})
    assert result["refused"] is False
    assert len(result["citations"]) >= 1

def test_an_unsupported_question_is_refused_not_answered(ask_deps):
    """The refusal is a graph edge, not a prompt instruction."""
    graph = build_ask_graph(ask_deps(hits=[]))
    result = graph.invoke({"question": "What is Sonatype's 2027 revenue forecast?"},
                          config={"configurable": {"thread_id": "a2"}})
    assert result["refused"] is True
    assert "grounded evidence" in result["reason"].lower()

def test_the_tool_loop_is_capped(ask_deps):
    deps = ask_deps(hits=[HIT_A], always_call_tools=True)
    graph = build_ask_graph(deps)
    graph.invoke({"question": "loop forever"}, config={"configurable": {"thread_id": "a3"}})
    assert deps.tool_calls <= 4

def test_an_answer_whose_claims_are_not_in_the_hits_is_refused(ask_deps):
    """The grounding gate runs AFTER the loop and before the answer."""
    graph = build_ask_graph(ask_deps(hits=[HIT_A], model_answer="JFrog will be acquired in 2027."))
    result = graph.invoke({"question": "any"}, config={"configurable": {"thread_id": "a4"}})
    assert result["refused"] is True

def test_tools_are_read_only_and_ledger_scoped(ask_deps):
    from agent.tools.ledger import TOOLS
    names = {t.name for t in TOOLS}
    assert names <= {"search_signals", "get_claim", "claim_history", "compare_entities", "list_sources"}
    assert not any("fetch" in n or "write" in n or "delete" in n for n in names)
```

- [ ] **Step 2–4: Run, implement, run**

Graph: `classify_intent → tool_loop (max 4) → grounding_gate → answer | refuse`.
Tools take and return plain data via the retrieval port. **No fetch tool, no write tool.**

Run: `docker compose run --rm api pytest tests/test_ask_graph.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: Ask graph with bounded tool loop and grounding gate"
```

---

### Task 9 [MUST]: Digest assembly

**Files:**
- Create: `backend/app/services/delivery/assembly.py`
- Test: `tests/test_assembly.py`

- [ ] **Step 1: Write the failing test**

```python
def test_the_budget_is_absolute_regardless_of_score(session, many_high_scoring_signals):
    digest = assemble(session, "sales", cfg=CFG, as_of=NOW)
    assert len(digest.items) == CFG.materiality.budget["sales"]

def test_one_busy_competitor_cannot_monopolise_a_digest(session, twenty_sonatype_signals):
    digest = assemble(session, "product", cfg=CFG, as_of=NOW)
    from collections import Counter
    assert max(Counter(i["entity"] for i in digest.items).values()) <= CFG.materiality.max_per_entity

def test_silent_entities_are_a_first_class_output(session, signals_for_sonatype_only):
    digest = assemble(session, "product", cfg=CFG, as_of=NOW)
    assert "harbor" in digest.silent_entities

def test_interrupts_bypass_the_budget(session, cross_assertion_signal, many_high_scoring_signals):
    digest = assemble(session, "sales", cfg=CFG, as_of=NOW)
    assert len(digest.interrupts) == 1
    assert len(digest.items) == CFG.materiality.budget["sales"]

def test_signals_below_the_persona_threshold_are_excluded(session, low_scoring_signals):
    assert assemble(session, "exec", cfg=CFG, as_of=NOW).items == []
```

- [ ] **Step 2–4: Run, implement per ARCHITECTURE §9, run**

Run: `docker compose run --rm api pytest tests/test_assembly.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: digest assembly with budget, diversity cap and silent entities"
```

---

### Task 10 [CUT-4]: Email rendering and delivery

**Files:**
- Create: `backend/app/services/delivery/email.py`, `backend/app/services/delivery/templates/digest.html.j2`
- Test: `tests/test_email.py`

- [ ] **Step 1: Write the failing test**

```python
def test_one_template_renders_all_three_personas_differently(sample_digests):
    from app.services.delivery.email import render_digest
    sales = render_digest(sample_digests["sales"], cfg=CFG)
    exec_ = render_digest(sample_digests["exec"], cfg=CFG)
    assert sales.subject != exec_.subject
    assert sales.html != exec_.html

def test_css_is_inlined_because_mail_clients_strip_style_blocks(sample_digests):
    html = render_digest(sample_digests["sales"], cfg=CFG).html
    assert "<style" not in html
    assert "style=" in html

def test_every_item_links_back_into_the_app(sample_digests):
    html = render_digest(sample_digests["sales"], cfg=CFG).html
    assert CFG.delivery.app_base_url in html

def test_an_empty_digest_still_sends_and_reports_stability(empty_digest):
    result = render_digest(empty_digest, cfg=CFG)
    assert "no material" in result.html.lower()

def test_send_records_a_delivery_row_and_never_calls_smtp_in_tests(session, fake_smtp, sample_digests):
    from app.services.delivery.email import send_digest
    send_digest(session, sample_digests["sales"], smtp=fake_smtp, cfg=CFG)
    from app.models.delivery import Delivery
    assert session.query(Delivery).count() == 1
    assert fake_smtp.sent == 1
```

- [ ] **Step 2–4: Run, implement with Jinja2 + `css_inline` + `smtplib`, run**

Run: `docker compose run --rm api pytest tests/test_email.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: persona-parameterised email digest with inlined CSS"
```

---

### Task 11 [MUST]: Read endpoints

**Files:**
- Create: `backend/app/routers/{runs,signals,digests,comparison,claims,industry,sources,config,coverage,email_preview,ask}.py`, matching controllers
- Modify: `backend/app/main.py` (mount routers)
- Test: `tests/test_api_reads.py`

**Every response must validate against its fixture in `client/src/fixtures/`.**

- [ ] **Step 1: Write the failing test — fixture-driven**

```python
import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "client" / "src" / "fixtures"

CASES = [
    ("/runs/latest", "run_status.json"),
    ("/activity/since-last-visit", "since_last_visit.json"),
    ("/signals?persona=sales", "signals_sales.json"),
    ("/digests/exec/weekly", "digest_exec_weekly.json"),
    ("/comparison?competitor=sonatype", "comparison_sonatype.json"),
    ("/claims?subject=jfrog", "claims_about_jfrog.json"),
    ("/industry", "industry_feed.json"),
    ("/sources", "sources.json"),
    ("/config/materiality", "materiality_weights.json"),
    ("/config/watchlist", "watchlist.json"),
    ("/coverage", "coverage_matrix.json"),
    ("/email/preview?persona=sales", "email_preview.json"),
]

@pytest.mark.parametrize("path,fixture", CASES)
def test_response_shape_matches_the_contract_fixture(client_with_data, path, fixture):
    expected = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    actual = client_with_data.get(path).json()
    assert _shape(actual) == _shape(expected), f"{path} diverges from {fixture}"

def _shape(value):
    """Compare structure and types, not values."""
    if isinstance(value, dict):
        return {k: _shape(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_shape(value[0])] if value else []
    return type(value).__name__

def test_list_endpoints_use_the_items_total_cursor_envelope(client_with_data):
    body = client_with_data.get("/signals?persona=product").json()
    assert {"items", "total", "cursor"} <= set(body)

def test_timestamps_carry_a_utc_offset(client_with_data):
    body = client_with_data.get("/runs/latest").json()
    assert body["last_run_at"].endswith("+00:00")
```

- [ ] **Step 2–4: Run, implement, run**

Run: `docker compose run --rm api pytest tests/test_api_reads.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: read endpoints matching the verified API contract"
```

---

### Task 12 [CUT-1]: Write endpoints

**Files:**
- Create: routers/controllers for `POST /runs`, `POST /signals/{id}/actions`, `PATCH /sources/{id}`, `PUT /config/materiality`, `PUT /config/watchlist`, `POST /ask`
- Test: `tests/test_api_writes.py`

- [ ] **Step 1: Write the failing test**

```python
def test_an_analyst_action_is_persisted_with_actor_and_reason(client_with_data):
    response = client_with_data.post("/signals/1/actions",
                                     json={"action": "reject", "reason": "duplicate", "actor": "a@jfrog.com"})
    assert response.status_code == 201

def test_changing_a_weight_rescore_without_re_inference(client_with_data):
    """Re-scoring the ledger is a SQL update, not re-running the model."""
    before = client_with_data.get("/signals?persona=sales").json()["items"][0]["score"]
    client_with_data.put("/config/materiality",
                         json={"modifiers": {"subject_is_jfrog": 1.0}})
    after = client_with_data.get("/signals?persona=sales").json()["items"][0]["score"]
    assert after != before

def test_invalid_config_is_rejected_with_a_readable_message(client_with_data):
    response = client_with_data.put("/config/materiality",
                                    json={"modifiers": {"reliability_grade": {"A": "not a number"}}})
    assert response.status_code == 422
    assert "message" in response.json()["error"]

def test_manual_run_invokes_the_same_job_the_scheduler_calls(client_with_data, spy_jobs):
    client_with_data.post("/runs", json={"kind": "collect"})
    assert spy_jobs.called == "run_collection"
```

- [ ] **Step 2–4: Run, implement, run**

Run: `docker compose run --rm api pytest tests/test_api_writes.py -v` → PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: write endpoints for analyst actions and configuration tuning"
```

---

### Task 13 [MUST]: Delivery jobs and the Day 3 milestone

**Files:**
- Modify: `backend/worker/jobs.py` (add `run_digest`), `backend/worker/scheduler.py`
- Test: `tests/test_delivery_job.py`

- [ ] **Step 1: Write the failing test**

```python
def test_digest_job_writes_a_run_row_per_persona(session, fake_smtp):
    from worker.jobs import run_digest
    report = run_digest(session=session, smtp=fake_smtp)
    from app.models.delivery import DigestRun
    assert session.query(DigestRun).count() == 3

def test_exec_digest_only_runs_on_its_configured_day(session, fake_smtp, monkeypatch):
    """A daily executive email is how this product dies in week two."""
    from worker.jobs import personas_due
    monkeypatch.setattr("worker.jobs.today_name", lambda: "TUE")
    assert "exec" not in personas_due(cfg=CFG)
    monkeypatch.setattr("worker.jobs.today_name", lambda: "FRI")
    assert "exec" in personas_due(cfg=CFG)
```

- [ ] **Step 2–4: Run, implement, run**

Add to the scheduler: `run_digest` at 07:00 daily; the job itself decides which personas are
due, so the executive roll-up fires only on its configured day.

- [ ] **Step 5: Run the entire suite**

Run: `docker compose run --rm api pytest -v`
Expected: every test from Plans 1, 2 and 3 PASSES

- [ ] **Step 6: Verify the Day 3 milestone**

```bash
docker compose up -d
curl -X POST http://localhost:8000/runs -d '{"kind":"collect"}' -H 'Content-Type: application/json'
curl http://localhost:8000/digests/sales
curl http://localhost:8000/comparison?competitor=sonatype
curl http://localhost:8000/coverage
curl -X POST http://localhost:8000/ask -d '{"question":"What does Sonatype claim about JFrog pricing?"}' -H 'Content-Type: application/json'
```

Expected: a populated sales digest; a comparison table whose JFrog cells are marked
`authored` and whose competitor cells carry grades and evidence; a coverage matrix reporting
gaps; and a grounded Ask answer with citations. **Then ask it something the ledger cannot
support and confirm it refuses.**

- [ ] **Step 7: Commit**

```bash
git add backend/worker tests/test_delivery_job.py
git commit -m "feat: digest delivery jobs — Day 3 backend milestone"
```

---

## Self-review notes

**Spec coverage.** Implements R5.1–R5.7, R6.3, R6.4, R6.5, R7.1, R7.2, R7.3, R7.5, and closes contract gaps G1, G2, G3, G5, G6, G7, G9, G12, G15.

**Gaps deliberately left open**, so they are not mistaken for oversights:
- **G4** (named-account overlap) requires CRM data and is out of scope per PRD §10. **Remove it from the mockup** rather than implementing it.
- **G8** — archive timeline milestone captions are editorial. Counts, dates and sizes are derived; captions are not stored.
- **G13** — credibility on a marketing claim like "80% more accurate" is analyst-assigned until corroboration inputs exist. The API exposes it as analyst-set, not computed.
- **G11** — cosmetic-versus-substantive classification ships without measured accuracy. The evaluation harness is Plan 5 / roadmap.
- **G14** was not a gap: one signal legitimately routes to several personas, so `delivered` exceeds `material`.
- `crossref` in the Interpret graph can now be wired to the retrieval service (Task 7). Doing so is optional in this plan; model adjudication (R3.6) remains roadmap.

**Documentation corrections to make while implementing:** DESIGN §3 lists collection modes as `feed|snapshot` and must include `api` as first-class — §4 already describes all three. The mockup's eight-column coverage matrix becomes nine.

**Type consistency.** `Element`, `ElementKind`, `Signal`, `Claim`, `ClaimVersion`, `Evidence` and `ScoreBreakdown` are consumed exactly as Plans 1–2 defined them. `ComparisonCell.grade` is `None` for both `authored` and `absent` origins — the only two cases where no capture exists to verify against.

**Remaining after this plan:** Plan 4 — the React client, ~8 tasks, built against `client/src/fixtures/` and then pointed at these endpoints. It is the lowest-risk plan in the sequence because the mockup and fixtures already exist and the contract is verified.
