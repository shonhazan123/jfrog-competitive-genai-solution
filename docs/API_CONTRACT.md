# API_CONTRACT — derived from the approved mockup

| | |
|---|---|
| **Status** | Contract draft · pre-implementation |
| **Date** | 26 August 2026 |
| **Source of truth** | [docs/mockup/demo.html](./mockup/demo.html) — WHAT each screen needs |
| **Production model** | [ARCHITECTURE.md](./ARCHITECTURE.md) §3, §9 · [DESIGN.md](./DESIGN.md) §3 — HOW data is produced |
| **Requirements** | [PRD.md](./PRD.md) §5 (R1.1…R7.5), §6 (taxonomy), §7 (Admiralty) |

This document is a **contract and gap analysis**, not application code. It documents the HTTP
surface implied by the approved mockup, screen by screen, and ends with the single most valuable
section — **"Displayed but not yet producible"** — enumerating everything a screen shows that the
pipeline described in ARCHITECTURE/DESIGN cannot currently produce.

The contract is derived strictly from the mockup. Endpoints for capabilities the mockup does not
show are not invented; data the mockup displays is not omitted.

---

## 0. Conventions (apply to every endpoint)

- **Timestamps** are ISO 8601 with an explicit UTC offset (`2026-08-26T06:00:00+00:00`). Never
  naive. The mockup renders friendly forms ("06:00 today", "24 Aug 2026"); the API always carries
  the machine form and the client formats.
- **Enums** match the canonical vocabulary below (config/*.yaml does not exist yet, so these are
  derived from PRD §6, DESIGN §3, and cross-checked against the mockup). Any mismatch is flagged in
  the gap list.
- **List endpoints** return `{ "items": [...], "total": int, "cursor": str | null }`.
- **Errors** return `{ "error": { "code": str, "message": str } }` with a message safe to show a
  non-technical analyst (N6).
- **Score breakdowns** travel as **ordered `[label, value]` pairs** so the UI renders the arithmetic
  without recomputing (R4.2). The order is the display order.
- **Evidence objects** always carry: `quote`, `source_url`, `source_name`, `captured_at`,
  `reliability_grade`, `credibility_score` (R5.4, N5).
- **Anything an analyst can tune is readable AND writable via the API** — materiality weights,
  watchlist, source enable/disable (R4.3, R7.3). No YAML-only config surface is exposed as
  read-only.

### Canonical enums

```python
SignalType = Literal[            # PRD §6, nine values (positioning has self/cross flavours)
    "product_capability", "positioning_messaging", "pricing_packaging",
    "security_trust", "corporate_financial", "partnership_ecosystem",
    "customer_evidence", "market_regulatory", "talent_org",
]
Persona          = Literal["sales", "product", "exec"]       # + "analyst" as consumer, PRD §3
ReliabilityGrade = Literal["A", "B", "C", "D", "E", "F"]      # Admiralty source reliability, PRD §7
CredibilityScore = Literal[1, 2, 3, 4, 5, 6]                  # Admiralty information credibility
ChangeKind       = Literal["new", "substantive", "cosmetic", "removed"]   # DESIGN §3 claim_version
CollectionMode   = Literal["feed", "snapshot", "api"]         # DESIGN §3 source.mode (api added §9)
SourceKind       = Literal["atom", "rss", "html_page", "api", "sitemap"]  # DESIGN §3 source.kind
ClaimType        = Literal["capability", "pricing", "positioning", "security"]  # DESIGN §3
AnalystAction    = Literal["confirm", "reject", "edit", "suppress"]       # DESIGN §3 analyst_action
Handling         = Literal["caution"]                         # PRD §6 security_trust in sales view
Provenance       = Literal["live", "archive"]                 # DESIGN §3 raw_capture.provenance
```

### Shared shapes

```python
class Evidence(TypedDict):
    quote: str                         # verbatim, cut from the capture by code (ARCH §5)
    source_url: str
    source_name: str
    captured_at: str                   # ISO 8601 + offset
    reliability_grade: ReliabilityGrade
    credibility_score: CredibilityScore
    is_primary: bool

class ScoreBreakdown(TypedDict):
    total: float
    parts: list[tuple[str, float]]     # ORDERED [label, value] pairs — UI renders as-is

class EntityRef(TypedDict):
    slug: str                          # jfrog | sonatype | gitlab | github | harbor | industry
    name: str
    tier: int | None                   # 1 = deep, 2 = news-only; null for industry pseudo-entity

class Change(TypedDict):               # structural / claim diff, rendered as was → now
    dimension: str                     # e.g. 'Malware detection' · cell 'JFrog'
    kind: ChangeKind
    was: str
    now: str

class TraceStep(TypedDict):            # one entry per Interpret node (ARCH §3 `trace`)
    n: int
    node: str                          # sanitize | detect | extract | verify | contextualize
    status: Literal["ok", "fail", "skipped"]
    detail: str

class Signal(TypedDict):
    id: str
    entity: EntityRef                  # who the signal is filed under
    signal_type: SignalType
    signal_flavour: Literal["self", "cross"] | None   # only for positioning_messaging
    subject_entity: str | None         # who it is ABOUT (slug)
    asserting_entity: str              # who SAYS it (slug)
    mentions_jfrog: bool
    headline: str
    occurred_at: str
    persona: Persona | None            # which persona's so_what is included
    so_what: str                       # the persona-specific "why do I care"
    score: float
    score_breakdown: ScoreBreakdown | None
    handling: Handling | None          # 'caution' on competitor security_trust in sales view
    awareness_only: bool               # 'awareness only — no action' tag
    change: Change | None              # present when produced by a structural/claim diff
    evidence: list[Evidence]
    cluster_id: str | None
    corroboration_count: int
    interrupt_tier: Literal["critical"] | None
```

---

## 1. Today (mockup screen ①, `#panel-today`)

Shows: the persistent **status strip**, a **"since you last looked"** banner, the ONE cross-assertion
**interrupt card** (with a "how was this produced" trace and score arithmetic), a **run funnel**, a
mixed **card grid**, and a teaching **empty state**.

### 1.1 `GET /runs/latest` — run status strip + funnel
- **Purpose:** power the persistent status strip (`Last run · sources · collected · clustered ·
  material · next run`) and the "Today's run funnel". Serves R6.1.
- **Params:** none.
- **Response:**

```python
class RunStatus(TypedDict):
    run_id: str
    started_at: str                    # ISO 8601 + offset  ("06:00 today")
    finished_at: str | None
    status: Literal["ok", "running", "failed"]
    next_run_at: str                   # "06:00 tomorrow"
    live: bool                         # green dot
    sources_count: int                 # 23
    funnel: list[tuple[str, int]]      # ORDERED: [("collected",94),("clustered",41),
                                        #           ("material",11),("delivered",14)]
    delivered_breakdown: list[tuple[str, int]]  # [("sales",6),("product",8),("exec",0)]
```
- **Consumed by:** every screen (status strip is persistent); Today (funnel card).

### 1.2 `POST /runs` — manual trigger ("▸ Run now")
- **Purpose:** trigger the same job path the scheduler runs (R6.2). Convenience, not a substitute.
- **Body:** `{ "reason": str | null }`
- **Response:** `202` → `{ "run_id": str, "status": "running", "started_at": str }`
- **Consumed by:** status strip `Run now` button (all screens).

### 1.3 `GET /activity/since-last-visit` — "since you last looked" (R7.5)
- **Purpose:** the banner *"Since you last looked: 12 new signals and 2 claim changes since your
  visit on 24 Aug"*. Depends on delivery/visit tracking (`digest_run` / `delivery`, DESIGN §3).
- **Params:** `actor` (str, the analyst identity; default current user).
- **Response:**

```python
class SinceLastVisit(TypedDict):
    last_visit_at: str                 # "24 Aug 2026"
    new_signals: int                   # 12
    claim_changes: int                 # 2
```
- **Consumed by:** Today (`.since` banner). *(See gap list — visit tracking.)*

### 1.4 `GET /signals` — filtered signal list
- **Purpose:** the Today grid, and the Sales/Product grids (screens ②③). This is the one list
  endpoint behind screens ②③④⑤ per DESIGN §9 ("one component with different queries").
  Serves R4.1, R4.5.
- **Query params:**

| param | type | default | notes |
|---|---|---|---|
| `persona` | Persona \| null | null | when set, `so_what`/`score` are that persona's; caution flag applied |
| `entity` | str \| null | null | filter by entity slug |
| `signal_type` | SignalType \| null | null | |
| `view` | `today` \| null | null | `today` = everything above materiality threshold, mixed types |
| `since` | str (ISO date) \| null | null | occurred_at lower bound |
| `until` | str (ISO date) \| null | null | occurred_at upper bound |
| `include_interrupts` | bool | true | interrupt-tier cards surfaced first |
| `limit` | int | 50 | |
| `cursor` | str \| null | null | opaque pagination cursor |

- **Response:** `{ "items": list[Signal], "total": int, "cursor": str | null }`
- **Consumed by:** Today grid; Sales grid (`?persona=sales`); Product grid (`?persona=product`).

### 1.5 `GET /signals/{signal_id}` — single signal with production trace
- **Purpose:** the interrupt card's **"How was this produced"** pipeline panel (ARCH §3 `trace`) and
  the **"show the arithmetic"** score breakdown (R4.2). Serves R3.1–R3.4.
- **Path:** `signal_id`.
- **Query:** `persona` (Persona | null) — selects which so_what/score to return.
- **Response:** a full `Signal` plus:

```python
class SignalDetail(Signal):
    trace: list[TraceStep]             # sanitize → detect → extract → verify → contextualize
    all_persona_scores: dict[str, ScoreBreakdown]   # sales/product/exec breakdowns
    bullet_classification: dict | None # product releases: {"parsed":40,"kept":3,"no_signal":37,
                                        #   "no_signal_detail":[("bug fix",22),("dep bump",11),
                                        #                        ("docs",4)]}
```
- **Consumed by:** Today interrupt card details; Product "Bullet classification" reveal.

### 1.6 `POST /signals/{signal_id}/actions` — analyst confirm/reject/edit/suppress
- **Purpose:** the four action buttons on every card (`✓ Confirm · ✗ Reject · ✎ Edit · 🔇 Mute`).
  Writes an `analyst_action` row (DESIGN §3). Serves R7.1; also the ±1 bounded adjustment R4.4.
- **Body:**

```python
class AnalystActionRequest(TypedDict):
    action: AnalystAction              # confirm | reject | edit | suppress
    actor: str
    reason: str | None                 # required for reject/suppress; free-text
    edit: dict | None                  # field-level overrides when action == "edit"
    relevance_adjustment: int | None   # R4.4: bounded [-1, +1], logged with reason
```
- **Response:** `{ "id": str, "target_type": "signal", "target_id": str, "action": AnalystAction,
  "actor": str, "at": str }`
- **Consumed by:** card action rows (all card screens). "🔇 Mute source" maps to
  `PATCH /sources/{id}` (§7.4) rather than an analyst_action.

---

## 2. Sales digest (mockup screen ②) and Product digest (screen ③)

Both are `GET /signals?persona=…` (§1.4) rendered as cards. The **digest** framing (budget, item
count, handling-caution count) comes from a distinct endpoint that mirrors the email.

### 2.1 `GET /digests/{persona}` — assembled per-persona digest
- **Purpose:** the digest as an assembled, budget-capped unit — the header counts (*"Six items…"*,
  *"8 items · 2 awareness-only"*) and the email body. Serves R6.3; assembly per ARCH §9.
- **Path:** `persona` ∈ {`sales`, `product`}. (`exec` is weekly — see §3.) Do not serve this
  payload from `/digests/exec/weekly`.
- **Implemented:** `backend/app/routers/digests.py` (`GET /{persona}`) →
  `backend/app/controllers/digests.py` (`persona_digest`). Operational note:
  [project-instruction/digests.md](./project-instruction/digests.md).
- **Query:** `date` (ISO date | null, default latest run).
- **Response:**

```python
class Digest(TypedDict):
    persona: Persona
    date: str
    subject: str                       # "Competitive digest — Sales · Tue 26 Aug"
    lead: str                          # intro paragraph
    budget: int                        # hard item cap (R4.5)
    item_count: int
    handling_caution_count: int        # sales: 1
    awareness_only_count: int          # product: 2
    items: list[Signal]                # already sorted, diversity-capped, budget-truncated
    silent_entities: list[dict]        # [{"entity":"sonatype","note":"No pricing changes …
                                        #    Checked 14 times.","checked_count":14,"window_days":30}]
```
- **Consumed by:** Sales grid header; Product grid header; Today empty-state teaching card;
  Email preview (§10).

---

## 3. Executive weekly roll-up (mockup screen ④)

### 3.1 `GET /digests/exec/weekly` — weekly executive roll-up
- **Purpose:** the four **trend** items (direction, velocity, confidence) plus the explicit
  **stability** statement. Deliberately weekly, permitted to report stability. Serves R6.4.
- **Query:** `week_of` (ISO date | null, default current week).
- **Response:**

```python
class Trend(TypedDict):
    id: str
    title: str
    body: str
    direction: Literal["toward_us", "against_us", "lateral"]   # "↑ toward us" / "↑ against us" / "→ lateral"
    velocity: Literal["accelerating", "steady", "emerging"]
    confidence_grade: ReliabilityGrade                          # "A" / "B"
    confidence_note: str               # "3 corroborating signals" / "single signal"
    contributing_signal_ids: list[str]

class StabilityStatement(TypedDict):
    title: str                         # "No material change in competitor positioning this week."
    detail: str                        # what was captured/diffed and found below threshold
    entities_checked: list[str]

class ExecWeekly(TypedDict):
    week_of: str
    assembled_at: str                  # "Friday"
    subject: str
    lead: str
    trends: list[Trend]                # 3
    stability: list[StabilityStatement]  # 1+
```
- **Consumed by:** Executive screen; Email preview (exec version).
- *(See gap list — direction / velocity / trends are not stored by the pipeline.)*

---

## 4. Comparison (mockup screen ⑤)

### 4.1 `GET /comparison` — JFrog-vs-competitor battlecard rows
- **Purpose:** the comparison table derived from the claim ledger (not hand-authored), each row
  expandable to its evidence, ⚠ marking recently-changed dimensions. Serves R5.1, R5.2, R5.4.
- **Query:** `competitor` (str, default `sonatype`); `changed_within_days` (int | null).
- **Response:** `{ "items": list[BattlecardRow], "total": int, "cursor": null }`

```python
class BattlecardRow(TypedDict):
    id: str                            # battlecard_row id
    dimension: str                     # "Malware detection"
    jfrog_position: str                # "Proactive; contextual analysis via Xray + Curation"
    competitor_position: str           # 'Claims JFrog is "very limited, not proactive"'
    competitor: str                    # entity slug
    supporting_claim_ids: list[str]    # DESIGN §3 battlecard_row.supporting_claim_ids[]
    reliability_grade: ReliabilityGrade | None    # from supporting claim; null when inferred
    credibility_score: CredibilityScore | None
    last_changed_at: str | None        # "24 Aug 2026" or null ("—")
    changed_recently: bool             # ⚠ flag (R5.2)
    evidence: list[Evidence]           # verbatim quote(s) behind the competitor cell
    change: Change | None              # was → now, when a claim changed
    no_claim_on_record: bool           # renders the "No competitor claim on record" empty teach
```
- **Consumed by:** Comparison table + expandable detail rows.
- *(See gap list — `jfrog_position` provenance; "inferred from absence" rows.)*

---

## 5. Competitors → Us (mockup screen ⑥)

The most differentiated view: what competitors publicly assert **about JFrog**, with history.
`subject_entity = jfrog`, `asserting_entity = <competitor>`.

### 5.1 `GET /claims` — claims about JFrog with version history
- **Purpose:** the four cross-assertion cards and the underlying claim records. Serves R5.3.
- **Query:**

| param | type | default | notes |
|---|---|---|---|
| `subject` | str | — | e.g. `jfrog` (who the claim is about) |
| `asserter` | str \| null | null | e.g. `sonatype` |
| `claim_type` | ClaimType \| null | null | |
| `include_history` | bool | true | include `versions[]` |

- **Response:** `{ "items": list[Claim], "total": int, "cursor": str | null }`

```python
class ClaimVersion(TypedDict):         # DESIGN §3 claim_version, append-only
    changed_at: str
    change_kind: ChangeKind
    old_text: str | None
    new_text: str
    evidence_id: str | None

class Claim(TypedDict):
    id: str
    subject_entity: str                # "jfrog"
    asserting_entity: str              # "sonatype"
    claim_text: str
    claim_type: ClaimType
    capability_tags: list[str]
    status: Literal["active"]          # v1 uses this value only (DESIGN §3)
    reliability_grade: ReliabilityGrade
    credibility_score: CredibilityScore
    first_seen_at: str
    last_confirmed_at: str
    score: float                       # materiality shown on the card (⚑ 95 / 71 / 64 / 60)
    change: Change | None              # was → now (malware card)
    evidence: list[Evidence]
    versions: list[ClaimVersion]       # history
```
- **Consumed by:** Competitors→Us cards.

### 5.2 `GET /claims/history/{source_id}` — archived version timeline
- **Purpose:** the timeline widget *"Sonatype's JFrog comparison page, 2021 → 2026 · 19 archived
  content versions"* backfilled from the web archive (R1.5). Serves R5.3 (history) and the backfill
  provenance (DESIGN §4).
- **Path:** `source_id` (the tracked comparison page source).
- **Response:**

```python
class ArchiveVersion(TypedDict):
    captured_at: str                   # archive timestamp (fetched_at, provenance="archive")
    label: str                         # "First archived version — feature checklist only"
    is_milestone: bool
    size_bytes: int | None             # 20KB → 38KB growth
    provenance: Provenance             # "archive"

class ArchiveTimeline(TypedDict):
    source_id: str
    source_url: str
    method: str                        # "Wayback CDX (collapse=digest)"
    total_versions: int                # 19
    sampled: bool                      # true — "sampled, not continuous"
    span_start: str                    # Feb 2021
    span_end: str                      # May 2026
    versions: list[ArchiveVersion]
```
- **Consumed by:** Competitors→Us timeline.
- *(See gap list — per-year version counts, size growth, milestone labels.)*

---

## 6. Industry (mockup screen ⑦)

### 6.1 `GET /industry` — DevSecOps field feed
- **Purpose:** the industry news grid — `market_regulatory` (and a few `security_trust` /
  `partnership_ecosystem`) signals filed under the `industry` pseudo-entity. Nothing about a
  competitor. Serves the "insights across our industry" half of the brief.
- **Query:** `signal_type` (SignalType | null); `standard` (str | null, e.g. `EU CRA`, `NIS2`,
  `SLSA`, `OpenSSF`, `CNCF`); `limit`; `cursor`.
- **Response:** `{ "items": list[IndustryItem], "total": int, "cursor": str | null }`

```python
class IndustryItem(TypedDict):
    id: str
    standard_chip: str                 # "EU CRA" / "NIS2" / "SLSA" / "OpenSSF" / "CNCF" / "SUPPLY CHAIN"
    signal_type: SignalType            # market_regulatory | security_trust | partnership_ecosystem
    headline: str
    body: str
    occurred_at: str
    evidence: Evidence                 # single source with grade
```
- **Consumed by:** Industry grid. (This is a specialised view of `/signals?entity=industry`; kept
  separate because the mockup renders it as blog-style news, not analyst cards.)

---

## 7. Settings (mockup screen ⑨)

### 7.1 `GET /sources` — source list with compliance
- **Purpose:** the sources table (mode, grade, cadence, robots decision, last checked) including
  **excluded** sources shown *as excluded, with the reason*. Serves R1.2, R7.3, PRD §8.
- **Query:** `entity` (str | null); `include_excluded` (bool, default true).
- **Response:** `{ "items": list[Source], "total": int, "cursor": null }`

```python
class Source(TypedDict):
    id: str
    name: str                          # "GitHub Releases (nexus-public)"
    entity: str                        # entity slug or "all"
    kind: SourceKind                   # atom | rss | html_page | api | sitemap
    mode: CollectionMode               # feed | snapshot | api
    reliability_grade: ReliabilityGrade | None
    credibility_score: CredibilityScore | None
    check_frequency: str               # "1h" / "6h" / "24h" / "12h"
    robots_allowed: bool               # ✓ / ✗
    requires_js: bool
    last_checked: str | None           # "06:00 today"
    enabled: bool
    excluded: bool
    exclusion_reason: str | None       # "excluded — blocked by robots.txt" /
                                        # "excluded — ToS prohibits automated collection (G2)"
```
- **Consumed by:** Settings → Sources table.

### 7.2 `GET /config/materiality` — materiality weights (readable)
- **Purpose:** the tunable weight controls. Serves R4.3, R7.3.
- **Response:**

```python
class MaterialityWeight(TypedDict):
    key: str                           # "subject_is_jfrog" / "tier_1_bonus" / "substantive_bonus" /
                                        # "recency_halflife_days" / "sales_budget" / "interrupt_cvss"
    label: str                         # "JFrog is the subject (multiplier)"
    value: float                       # 2.0 / 15 / 20 / 14 / 6 / 8.0
    min: float
    max: float
    step: float
    note: str
    unit: Literal["multiplier", "points", "days", "items", "cvss"]

class MaterialityConfig(TypedDict):
    config_version: int
    weights: list[MaterialityWeight]   # ORDERED as displayed
```

### 7.3 `PUT /config/materiality` — materiality weights (writable, R4.3)
- **Body:** `{ "weights": list[{"key": str, "value": float}], "actor": str }`
- **Response:** updated `MaterialityConfig` with bumped `config_version`. Changing a weight re-ranks
  the ledger (a DB update); the response echoes the new version so the client can refetch scores.

### 7.4 `PATCH /sources/{source_id}` — enable/disable / mute (writable, R7.3)
- **Body:** `{ "enabled": bool | null, "actor": str, "reason": str | null }`
- **Response:** updated `Source`.
- **Consumed by:** Settings source toggles; card "🔇 Mute source" button.

### 7.5 `GET /config/watchlist` — watchlist terms (readable, R4.3)
- **Response:**

```python
class Watchlist(TypedDict):
    config_version: int
    terms: list[str]                   # ["malware detection","SBOM","model registry","cargo",
                                        #  "SLSA provenance","hidden costs","runtime security",
                                        #  "contact sales"]
```

### 7.6 `PUT /config/watchlist` — watchlist terms (writable, R4.3)
- **Body:** `{ "terms": list[str], "actor": str }`
- **Response:** updated `Watchlist` with bumped `config_version`. Re-ranks the ledger.

### 7.7 `GET /coverage` — collection coverage matrix
- **Purpose:** the entities × signal-types grid, surfacing configured gaps (✗) and non-applicable
  cells (—). Serves R5.5.
- **Response:**

```python
class CoverageCell(TypedDict):
    signal_type: SignalType | Literal["positioning", "market_regulatory"]  # column key
    status: Literal["multiple", "one", "gap", "not_applicable"]   # ✓✓ / ✓ / ✗ / —
    source_count: int

class CoverageRow(TypedDict):
    entity: str
    tier: int | None                   # "tier 1" chip on Sonatype
    cells: list[CoverageCell]          # ORDERED by column

class CoverageMatrix(TypedDict):
    caption: str
    columns: list[str]                 # ["product","security","market/reg","partnership",
                                        #  "talent","customer","positioning","pricing"]
    rows: list[CoverageRow]            # Sonatype, GitLab, GitHub, Harbor, Industry
    legend: list[tuple[str, str]]      # [("✓✓","multiple sources"), ...]
```
- **Consumed by:** Settings → coverage matrix.
- *(See gap list — columns collapse the 9-value taxonomy to 8; corporate_financial absent.)*

---

## 8. Ask (mockup screen ⑧)

### 8.1 `POST /ask` — grounded question answering
- **Purpose:** answer strictly from the ledger, render the evidence used, and **refuse** when the
  ledger cannot support an answer. Serves R6.5. (The mockup transcript is hardcoded; this is the
  live contract behind it.)
- **Body:** `{ "question": str, "persona": Persona | null }`
- **Response:**

```python
class AskEvidence(TypedDict):          # a numbered evidence card in the answer
    n: int
    quote: str
    source_url: str
    source_name: str
    captured_at: str
    reliability_grade: ReliabilityGrade
    credibility_score: CredibilityScore

class NearbyItem(TypedDict):
    text: str

class AskResponse(TypedDict):
    question: str
    grounded: bool                     # false → refusal
    answer: str                        # the prose; on refusal, the explanation
    evidence: list[AskEvidence]        # empty on refusal
    refusal_reason: str | None         # "No grounded evidence" when grounded == false
    nearby_evidence: list[NearbyItem]  # grounded fallbacks offered on refusal
```
- **Consumed by:** Ask transcript (answered, comparison, and refusal exchanges).
- **Note:** the retriever returns empty rather than widening (R5.7); empty retrieval triggers the
  refusal edge (`grounded: false`) **without calling the model**. Hits accumulate on the deps
  object (`deps.accumulated_hits`), not in checkpointed LangGraph state. The grounding gate
  routes on `AskState.refused` (not a `_route` key). Graph:
  `classify_intent → tool_loop (max 4) → grounding_gate → answer | refuse`.
  `POST /ask` bridges via `app/services/ask_service.py` → `agent.graphs.ask.graph`; `app/`
  never imports langgraph/openai literals. Operational note:
  [project-instruction/ask.md](./project-instruction/ask.md).

---

## 9. Email preview (mockup screen ⑩)

### 9.1 `GET /email/preview` — rendered digest email per persona
- **Purpose:** the inbox preview, parameterised by persona (sales/product/exec). Same evidence,
  different object. Serves R6.3 (and R6.4 for exec). This reuses `/digests/{persona}` +
  `/digests/exec/weekly` data but returns the email-shaped payload the mockup's JS renders.
- **Query:** `persona` (Persona, default `sales`); `date` (ISO date | null).
- **Response:**

```python
class EmailDigestItem(TypedDict):
    signal_type: str                   # "security_trust" / "trend ↑ against us" / "stability"
    headline: str
    so_what: str
    flag: str | None                   # "⚠ caution" / "awareness" / "stable"
    app_link: str                      # "Open in app →" deep link

class EmailPreview(TypedDict):
    persona: Persona
    from_name: str                     # "CI System"
    from_email: str                    # "ci-digest@example.internal"
    subject: str                       # "Competitive digest — Sales · Tue 26 Aug"
    meta: str                          # "6 items · 1 handling caution · budget capped"
    lead: str
    items: list[EmailDigestItem]
    sent_at: str                       # "06:05"
    delivery_logged: bool              # true
    footer: str
```
- **Consumed by:** Email preview screen (sales/product/exec toggle).

---

## Endpoint index

| # | Method | Path | Screen | Requirement |
|---|---|---|---|---|
| 1 | GET | `/runs/latest` | status strip · Today funnel | R6.1 |
| 2 | POST | `/runs` | status strip "Run now" | R6.2 |
| 3 | GET | `/activity/since-last-visit` | Today "since you last looked" | R7.5 |
| 4 | GET | `/signals` | Today / Sales / Product grids | R4.1, R4.5 |
| 5 | GET | `/signals/{id}` | Today interrupt trace · Product bullet reveal | R3.1–R3.4, R4.2 |
| 6 | POST | `/signals/{id}/actions` | card action buttons | R7.1, R4.4 |
| 7 | GET | `/digests/{persona}` | Sales / Product headers · Email | R6.3 |
| 8 | GET | `/digests/exec/weekly` | Executive roll-up · Email | R6.4 |
| 9 | GET | `/comparison` | Comparison table | R5.1, R5.2, R5.4 |
| 10 | GET | `/claims` | Competitors→Us cards | R5.3 |
| 11 | GET | `/claims/history/{source_id}` | Competitors→Us timeline | R5.3, R1.5 |
| 12 | GET | `/industry` | Industry grid | R5.5 lane |
| 13 | POST | `/ask` | Ask transcript | R6.5, R5.7 |
| 14 | GET | `/sources` | Settings sources | R1.2, R7.3, §8 |
| 15 | PATCH | `/sources/{id}` | source enable/disable · Mute | R7.3 |
| 16 | GET | `/config/materiality` | Settings weights (read) | R4.3, R7.3 |
| 17 | PUT | `/config/materiality` | Settings weights (write) | R4.3 |
| 18 | GET | `/config/watchlist` | Settings watchlist (read) | R4.3 |
| 19 | PUT | `/config/watchlist` | Settings watchlist (write) | R4.3 |
| 20 | GET | `/coverage` | Settings coverage matrix | R5.5 |
| 21 | GET | `/email/preview` | Email preview | R6.3, R6.4 |

**21 endpoints.**

---

## Displayed but not yet producible

Every item below is something a screen renders that the pipeline described in
[ARCHITECTURE.md](./ARCHITECTURE.md) and [DESIGN.md](./DESIGN.md) **cannot currently produce** from
stored data. These are reported, not designed around. Each: (a) what the UI shows, (b) what would be
needed, (c) v1 or roadmap.

### G1 — Executive trend "direction" (↑ toward us / ↑ against us / → lateral)
- **(a) UI shows:** each executive trend carries a direction arrow and phrase (screen ④; email exec).
- **(b) Needed:** the schema stores `signal` (an event) and `claim` (a state); nothing stores a
  *trend* or a *direction*. Direction requires aggregating multiple signals over time and computing a
  vector relative to JFrog's position. No `trend` table, no direction field, and R3.6 (adjudication
  of new vs. contradiction over time) is explicitly roadmap. DESIGN §3 has no trend entity.
- **(c) Roadmap.** v1 can only assemble the weekly roll-up from individually-scored signals; the
  direction is an analyst/editorial judgement, not a stored, derivable field.

### G2 — Executive trend "velocity" (accelerating / steady / emerging)
- **(a) UI shows:** velocity chip per trend (screen ④).
- **(b) Needed:** velocity is a second derivative over time-bucketed signal counts per theme. Nothing
  buckets signals into themes or stores counts-over-time. Clustering (ARCH §9) groups *one event
  across sources*, not *a theme across weeks*.
- **(c) Roadmap.** Requires theme aggregation and a time series the pipeline does not keep.

### G3 — Trend "confidence — N corroborating signals" as a trend-level grade
- **(a) UI shows:** "Confidence A — 3 corroborating signals" on a *trend* (screen ④).
- **(b) Needed:** corroboration_count exists per *signal cluster* (ARCH §9), not per trend. A trend
  spanning releases + hiring + messaging crosses clusters and signal types; no structure counts
  corroborating signals across that grouping.
- **(c) Roadmap** (depends on G1/G2 trend aggregation).

### G4 — "Named-account overlap flagged" (customer_evidence / sales cards)
- **(a) UI shows:** *"A new logo in a segment where JFrog has named-account overlap"* and *"Named-
  account overlap flagged to the competitive desk."* (Today customer_evidence card; Sales card).
- **(b) Needed:** account/deal data. This requires CRM records (Salesforce). PRD §10 puts win/loss
  and CRM data **out of scope entirely** for v1; the data model is only *designed* to attach internal
  primary evidence later.
- **(c) Roadmap (out of scope for v1).** The system can detect the new case-study logo, but cannot
  know JFrog has account overlap without CRM.

### G5 — "Checked N times" on empty/silent states
- **(a) UI shows:** *"No pricing changes for Sonatype in 30 days. Checked 14 times."* (Today empty
  teach; comparison c6; digest `silent_entities`; Competitors→Us "Checked weekly").
- **(b) Needed:** a count of checks over a window. `source.last_checked` stores only the *last* time,
  not a tally. `raw_capture` is append-only so a count is derivable **only for snapshot sources that
  persist a capture each check** — but conditional GET / 304 (R1.4) means unchanged pages produce **no
  new capture**, so "checked" ≠ "captured". A check counter is not stored.
- **(c) v1 achievable *if* a per-source check counter (or 304 log) is added; otherwise roadmap.**
  As designed today, "checked 14 times" is not derivable from stored data — flag.

### G6 — JFrog's own position in the comparison table (`jfrog_position`)
- **(a) UI shows:** every comparison row's "JFrog position" column, e.g. *"Proactive; contextual
  analysis via Xray + Curation"*, *"30+ formats native"* (screen ⑤); and battlecard "JFrog: AI
  Catalog + Xray" in Ask.
- **(b) Needed:** these read as authored assertions with **no source, quote, or evidence** attached.
  DESIGN §3 `battlecard_row.jfrog_position` is a plain string with no evidence link, unlike the
  competitor cell which links to a claim. The collection strategy (PRD §7) collects competitor and
  industry sources; **JFrog is not configured as a monitored source of self-claims**. So the JFrog
  column is effectively hand-seeded, contradicting R5.1's "derived from the ledger, not hand-
  authored" for that half of the table.
- **(c) v1: partial / hand-seeded.** Fully producing it requires monitoring JFrog's own pages as a
  source with graded evidence — otherwise the JFrog column is an assumption, not evidence. Flag.

### G7 — "Runtime security: no runtime claim on record" (inferred-from-absence row)
- **(a) UI shows:** comparison row c6 grades the competitor cell **C4 "inferred from absence"** with
  `last_changed = —` and an empty-state.
- **(b) Needed:** the pipeline records what a source *says*; it has no mechanism to assert *absence*
  ("no claim exists"). Absence-as-evidence is a negative inference over the whole corpus, and the
  retriever is explicitly forbidden from inventing results (R5.7). A grade on a non-existent claim has
  no capture to verify against (violates N5).
- **(c) Roadmap.** v1 can show "no claim on record" as a UI empty state, but the **C4 grade on an
  absence is not producible** — nothing to grade. Flag the grade specifically.

### G8 — Archive timeline richness: per-year version counts, size growth, milestone labels
- **(a) UI shows:** "2022 · 4 versions", "2024 · 6 versions", byte growth "20KB → 38KB", and curated
  milestone captions like *"Pricing 'hidden costs' language added"* (screen ⑥ timeline).
- **(b) Needed:** backfill (R1.5, DESIGN §4) stores each archived `raw_capture` with `fetched_at` and
  `content_hash`; **total count (19) and timestamps are derivable**, and **byte size is derivable if
  `blob` length is stored**. But *milestone semantics* ("this is the version where 'hidden costs' was
  added") require diffing consecutive archived versions and labelling the meaningful ones — that is
  claim_version diffing over the backfill, which the design does run, but the **human-readable
  milestone caption** is not a stored field.
- **(c) v1 partial:** counts/timestamps/sizes derivable; **milestone captions are editorial and not
  stored** — flag.

### G9 — "Since you last looked: 12 new signals and 2 claim changes" (unread state)
- **(a) UI shows:** the Today `.since` banner and Competitors→Us "Checked weekly" (R7.5).
- **(b) Needed:** per-user visit tracking. DESIGN §3 has `delivery` (what was sent) and `digest_run`,
  which support "since last **delivery**", but **not "since this user last opened the app"** — there
  is no `user_visit` / `last_seen` table. The count of "new since visit" needs a per-actor last-visit
  timestamp.
- **(c) v1 achievable *if* a visit/last-seen record is added (small); otherwise the banner is backed
  by last-delivery, not last-visit.** As currently modelled, per-user visit state is not stored — flag.

### G10 — Cross-assertion score arithmetic exact terms (`+ tier_1 +15`, `+ substantive +20`)
- **(a) UI shows:** ordered score breakdowns rendered as arithmetic (Today interrupt; product card
  66; screen shows `subject_is_jfrog ×2.0`, `tier_1 +15`, `substantive +20`, `watchlist "cargo" +12`,
  `source grade A +9`).
- **(b) Needed:** `score_breakdown` (JSONB) **is** stored per signal (DESIGN §3; ARCH §9
  `ScoreBreakdown.parts`), so this is producible — **with one caveat:** the coefficients come from
  `materiality.yaml`, which **does not exist yet** (per the task's enum context). Until config is
  seeded, the exact constants (`+15`, `+20`, `×2.0`, halflife 14) are placeholders.
- **(c) v1 (producible once config/materiality.yaml exists).** Flagged only as a config dependency,
  not a schema gap.

### G11 — "Substantive change +20" classification (change_kind on positioning diffs)
- **(a) UI shows:** the interrupt and comparison rows label the change **substantive** and score
  `+20` for it.
- **(b) Needed:** `claim_version.change_kind ∈ {new, substantive, cosmetic, removed}` exists (DESIGN
  §3, R2.4), so the label is storable and producible. Distinguishing *substantive* from *cosmetic*
  reliably is the "hard case" acknowledged in DESIGN §10 — producible, accuracy unmeasured in v1.
- **(c) v1 (producible; accuracy not measured).** Minor flag.

### G12 — Coverage-matrix column taxonomy vs. the 9-value signal enum
- **(a) UI shows:** 8 columns — product, security, market/reg, partnership, talent, customer,
  positioning, pricing (screen ⑨).
- **(b) Needed:** the canonical taxonomy has **nine** values. The matrix **collapses**
  `positioning_messaging` self+cross into one "positioning" column and **omits `corporate_financial`
  entirely**. If coverage is computed from `source × signal_type`, a column for corporate_financial
  should exist (even if all "—"), and positioning self/cross are one signal_type so collapsing is
  fine. Producible, but the column set must be reconciled with the enum.
- **(c) v1 (producible; enum reconciliation needed).** See enum mismatch notes below.

### G13 — "80% more accurate data than JFrog" credibility handling
- **(a) UI shows:** a cross-assertion claim graded **A3** ("possibly true — unverifiable marketing
  metric").
- **(b) Needed:** the quote is verbatim and verifiable against the capture (producible, N5). But the
  **credibility_score (3 = "possibly true")** is described as coming "from corroboration" (DESIGN §3);
  a marketing metric like "80%" has no corroborating source, so the 3 is an analyst/editorial
  assignment, not a corroboration-derived value. The independent-axis grading (reliability A from the
  source, credibility from corroboration) is honoured in shape, but the specific credibility value is
  not mechanically derivable.
- **(c) v1 partial:** grade is storable; the *value* is analyst-assigned until corroboration inputs
  exist. Minor flag.

### G14 — Funnel "delivered 14 (6 sales · 8 product)" and material=11 reconciliation
- **(a) UI shows:** funnel 94 → 41 → 11 material → 14 delivered; but 11 material vs 14 delivered
  (6+8) don't reconcile because a signal can route to multiple personas.
- **(b) Needed:** producible — `digest_run`/`delivery` record per-persona delivery, and materiality
  is per-persona (`materiality_sales/product/exec`). The apparent mismatch is expected (one signal
  delivered to two personas counts twice in "delivered", once in "material"). No gap; documented so
  the client doesn't treat it as an error.
- **(c) v1 (producible).** Documentation note, not a gap.

### G15 — "one other" competitor referenced but unnamed
- **(a) UI shows:** Competitors→Us empty-state: *"GitLab, GitHub, Harbor and one other are
  monitored"*; Exec stability *"all five tracked competitors"*.
- **(b) Needed:** the mockup names four competitors (Sonatype, GitLab, GitHub, Harbor) but implies a
  fifth. `entity` config would need to name it. Not a pipeline gap — a config/content gap.
- **(c) v1 (config).** Flag so the fifth entity is defined in entities config before this string is truthful.

---

## Enum mismatches and volume-balance discrepancies found

**Enum mismatches / naming to reconcile:**

1. **`positioning_messaging` is abbreviated to `positioning`** throughout the mockup (type chips
   "positioning · cross", "positioning · about JFrog"; coverage column "positioning"). The API uses
   the canonical `positioning_messaging` and adds `signal_flavour: "self" | "cross"` to carry the
   distinction the taxonomy encodes as two rows (PRD §6). Client must map the label.
2. **Coverage matrix omits `corporate_financial`** (8 columns for a 9-value enum) and **collapses
   positioning self/cross into one column** (G12). Reconcile the column set with `SignalType`.
3. **`market_regulatory` shown as "market/reg"** (coverage column) and **"—" (not applicable)** for
   all competitor rows, ✓✓ only for Industry — consistent with the design (industry-lane only), but
   the label is abbreviated.
4. **Collection mode `api`** appears in the sources table and DESIGN §9, but DESIGN §3's
   `source.mode` originally lists only `feed | snapshot`. The contract treats `api` as a first-class
   mode (§9 authoritative). Reconcile DESIGN §3.
5. **Admiralty grades observed:** A1, A2, A3, B2, B3, C4 — all within reliability A–F and credibility
   1–6. No out-of-range values. The `C4` on comparison row c6 is an *inferred-from-absence* grade
   with no capture (G7) — structurally questionable rather than out-of-range.
6. **`claim_type`** is not surfaced explicitly on any card; it is inferred (malware/AI → capability
   or positioning, "hidden costs" → pricing, "export only" → capability/positioning). The contract
   assigns it per DESIGN §3; the mockup does not display it, so no visible mismatch, but assignment is
   an implementation choice to confirm.

**Volume-balance discrepancies (target was ~40% product_capability, ~20% security_trust,
~15% market_regulatory, exactly ONE cross-assertion):**

The instruction says: if the mockup differs, **match the mockup and note it**. The mockup's actual
distribution across the signal cards it renders (Today grid + Sales + Product, deduped by card):

- **product_capability:** ~9 distinct cards (Nexus 3.95 Cargo, Nexus 3.95 release/40-bullets, HF
  Firewall, GitLab SLSA ×2 appearances, GitHub retention, Java 11 deprecation) — **the plurality,
  roughly in line with ~40%.**
- **security_trust:** the Nexus ≤3.94 advisory appears in Today, Sales (with caution), and Product —
  **~1 distinct signal shown 3 times (~15–20%).** In line.
- **market_regulatory:** EU CRA (Today + Sales), SLSA adoption (Product) — plus 6 Industry-lane items
  on screen ⑦. Counting only persona cards it is ~15%; **counting the Industry screen it is much
  higher.** Noted.
- **cross-assertion (`positioning_messaging` flavour=cross):** **exactly ONE** interrupt card
  (Sonatype → JFrog, malware detection), matching the "exactly one" requirement and PRD §6's "< 1/wk".
  The Competitors→Us screen shows 4 *cross-assertion claims* (claim records, not new signals) — these
  are history of the same rare event type, not four new cross signals. Fixtures keep **exactly one
  cross-assertion signal** and place the other three as claim-history records.
- **customer_evidence, partnership_ecosystem, talent_org** each appear (1–2 cards) — present in
  fixtures to mirror the mockup even though not in the target ratio.

**Discrepancy summary:** the mockup is product_capability-heavy (consistent with the target ~40%),
holds exactly one cross-assertion signal (consistent), but security_trust and market_regulatory
persona-card counts run a little under the 20%/15% targets *unless* the Industry screen is counted.
Per instruction, fixtures **match the mockup** rather than the abstract ratio, and this note records
the divergence.
