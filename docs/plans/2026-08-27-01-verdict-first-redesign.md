# Verdict-First Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This plan follows the repo convention (see `docs/plans/2026-08-26-04-client.md`): build each task with its tests, run the backend suite (`cd backend && python -m pytest`) and client suite (`cd client && npm test`) at the end of each phase.

**Goal:** Turn the current build — which is architected around change-detection and numeric scoring — into a verdict-first, single-snapshot daily intelligence tool where every screen hands the reader a judgement (plain tier + one-line reason) backed by a clickable source, with no numbers and no historical diffing on any surface.

**Architecture:** Keep the deterministic scoring engine as the *ranking* mechanism under the hood, but present its output as three plain tiers (Act on it / Worth knowing / Background) plus an LLM-authored one-line reason — the number never reaches the screen. Reframe the Competitors room around JFrog's own product components. Strip all diffing/versioning from the UX (the code stays in the repo as the roadmap story). Reframe Settings from numeric weights to intention-based config (competitors, keywords, instructions).

**Tech Stack:** Backend — FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, pytest + testcontainers (pgvector). Client — React 19, Vite, TypeScript, @tanstack/react-query, Vitest + Testing Library. LLM — langchain-openai via the agent package.

**Spec:** This plan implements the reconciled design agreed in session — see the "Design decisions (locked)" section below, which is the authoritative spec. Supporting references: `docs/API_CONTRACT.md` (current endpoint shapes), `docs/PRD.md` (§3 personas, §6 signal taxonomy), `config/*.yaml` (the tunable policy layer).

## Global Constraints

- **No numbers on any consumer screen.** Scores, Admiralty grades as bare letters, and score breakdowns must not appear on Today, Competitors, Signals, Industry, Divisions, or Email. Settings is the one carve-out and it too becomes intention-based (see Phase E). This rule is already stated in `config/labels.yaml:1`.
- **No diffing, no historical comparison, no "since last run" on any surface.** Single snapshot only. The backfill/`ClaimVersion`/timeline code remains in the repo but is removed from primary navigation and from every card.
- **Every claim carries a clickable source link and a date.** `Evidence.source_url` already exists in the payload (`client/src/api/types.ts:34`); the fix is rendering, not data.
- **Three personas stay: `sales` / `product` / `exec`.** Do not add `marketing`. Divisions and per-persona so-whats are kept.
- **Email Digest is kept** as a delivery surface.
- **Ask stays a skeleton** — do not build live chat in this plan.
- **Never pin dependency versions from memory** — this plan adds no new dependencies.
- Preserve the append-only invariant on `raw_capture` (`backend/app/models/capture.py:6`).

---

## Design decisions (locked)

| # | Decision |
|---|---|
| 1 | Keep per-division so-what (sales/product/exec). Divisions page stays. |
| 2 | Competitors room is reframed around **JFrog's own components** (Artifactory, Xray, Curation, AppTrust, Advanced Security, Runtime Security, AI/ML) as the rows, competitors across, click-to-expand cells. |
| 3 | Source link + date on **every** claim/card — audit and enforce. |
| 4 | Email Digest stays. |
| 5 | Config is **intention-based** (add competitors, add keywords, add instructions), not numeric. Remove the numeric weight editor from the UI. |
| 6 | **Hybrid scoring:** deterministic engine ranks; UI shows tier + LLM one-line reason, never the number. |
| 7 | Ask = skeleton for now. |
| 8 | No diffing / no historical / single-snapshot daily digest. |

---

## The Wow — the North Star every task serves

The demo moment we are building toward: **a non-technical CI manager opens Today and, in under 90 seconds, knows the one thing that matters and why — and can click straight to the primary source to trust it.** Not fifty items; five. Not a score of 73; "Act on it — directly targets Artifactory's SBOM story." Not "what changed since yesterday"; "what matters right now."

Every task below states the *product outcome* it produces, not just the code. If a change does not move the reader closer to "handed a judgement they can trust and act on," it is wrong even if the tests pass. The failure mode we are designing against is a wall of text that makes the reader do the analysis themselves.

---

## File structure

**Backend (create):**
- `config/jfrog_components.yaml` — the JFrog component registry + dimension mapping (Task 6).
- `config/themes.yaml` — the stable industry theme set (Task 8).
- `config/instructions.yaml` — analyst free-text instructions (Task 9).
- `backend/app/services/comparison_matrix.py` — component × competitor matrix builder (Task 6).
- `backend/app/services/industry_themes.py` — deterministic theme assignment (Task 8).
- `backend/app/services/today_brief.py` — the daily headline verdict composer (Task 5).
- `backend/alembic/versions/<hash>_add_why_it_matters.py` — migration for the new column (Task 2).

**Backend (modify):**
- `config/materiality.yaml` — add `tiers` thresholds (Task 2).
- `config/labels.yaml` — replace numeric `priority_bands` with `tiers` labels (Task 2).
- `backend/app/services/scoring/materiality.py` — add `tier_for` + `primary_stakeholder` (Task 2).
- `backend/app/models/signal.py` — add `why_it_matters` column (Task 2).
- `backend/agent/prompts/contextualize.md` + `backend/agent/nodes/contextualize.py` — emit `why_it_matters` (Task 2).
- `backend/app/services/agent_service.py` — persist `why_it_matters` (Task 2).
- `backend/app/controllers/signals.py` — serialize `tier`, `primary_stakeholder`, `why_it_matters`; stop emitting `change` (Tasks 2, 4).
- `backend/app/controllers/comparison.py` — drop `changed_recently`/`last_changed_at`/`change`; add matrix route (Tasks 4, 6).
- `backend/app/controllers/config.py` — competitors + instructions endpoints (Task 9).
- `backend/app/controllers/industry.py` — theme endpoints (Task 8).
- `backend/app/main.py` — register new routes (Tasks 5, 6, 8, 9).

**Client (create):**
- `client/src/components/TierBadge.tsx` (Task 3).
- `client/src/components/ComparisonGrid.tsx` (Task 6).
- `client/src/pages/Signals.tsx` (Task 7).
- `client/src/pages/ThemePage.tsx` (Task 8).
- `client/src/components/CompetitorEditor.tsx`, `client/src/components/InstructionsEditor.tsx` (Task 9).

**Client (modify):**
- `client/src/api/types.ts` — add tier types; extend `Signal`; add matrix + theme types (Tasks 2, 6, 8).
- `client/src/config/labels.ts` — tier labels + hues (Task 3).
- `client/src/components/SignalCard.tsx` — source link, tier badge + reason, remove numbers/diffing (Tasks 1, 3, 4).
- `client/src/pages/Industry.tsx` — source link + theme tiles (Tasks 1, 8).
- `client/src/pages/Today.tsx` — headline verdict + ranked cards (Task 5).
- `client/src/components/ComparisonTable.tsx` — remove diffing columns (Task 4) — or retire in favour of `ComparisonGrid`.
- `client/src/pages/Comparison.tsx` — render the grid (Task 6).
- `client/src/pages/Settings.tsx` — remove `WeightEditor`, add editors (Task 9).
- `client/src/config/navigation.ts` + `client/src/app/routes.tsx` — new IA (Task 10).

---

## Phase A — Trust & the plain-tier core (Tasks 1–4)

### Task 1: Source is always a clickable link

**Wow objective:** Trust is a feature. A reader must be one click from the primary source on *every* card — a CI verdict with no traceable source is worthless in a real deal. Two cards currently print the source as dead text.

**Files:**
- Modify: `client/src/components/SignalCard.tsx:168-174` (the `signal-card__source-line`)
- Modify: `client/src/pages/Industry.tsx:119-134` (the evidence source line inside `IndustryCard`)
- Test: `client/src/components/SignalCard.test.tsx`, `client/src/pages/grids.test.tsx`

**Interfaces:**
- Consumes: `Evidence.source_url`, `Evidence.source_name`, `Evidence.captured_at` (already present, `client/src/api/types.ts:34-42`).
- Produces: nothing new — a rendering fix other tasks assume.

- [ ] **Step 1: Write the failing test** — assert the source renders as an anchor with the right href.

```tsx
// in SignalCard.test.tsx
it("renders the evidence source as a link to source_url", () => {
  render(<SignalCard signal={fixture} persona="sales" />);
  const link = screen.getByRole("link", { name: fixture.evidence[0].source_name });
  expect(link).toHaveAttribute("href", fixture.evidence[0].source_url);
});
```

- [ ] **Step 2: Run it, verify it fails** — `cd client && npm test -- SignalCard` → FAIL (no link role).

- [ ] **Step 3: Implement** — replace the `<span>{evidence.source_name}</span>` with an anchor. Keep the date and drop the bare `GradeChip` letter (see Task 3 for the grade treatment).

```tsx
<p className="signal-card__source-line">
  <a href={evidence.source_url} target="_blank" rel="noreferrer">{evidence.source_name}</a>
  <span aria-hidden="true"> · </span>
  <span>{formatDate(evidence.captured_at)}</span>
</p>
```

- [ ] **Step 4: Repeat for `IndustryCard`** — same anchor swap around `item.evidence.source_name`, keeping the `formatDate(item.evidence.captured_at)`.

- [ ] **Step 5: Run tests, verify pass**, then commit.

```bash
git add client/src/components/SignalCard.tsx client/src/pages/Industry.tsx client/src/components/SignalCard.test.tsx client/src/pages/grids.test.tsx
git commit -m "fix(client): render every evidence source as a clickable link"
```

---

### Task 2: Deterministic tier + LLM one-line reason (the hybrid core)

**Wow objective:** This is the heart of the redesign. The reader sees "Act on it — directly targets Artifactory's SBOM story," never "73." The tier is computed by transparent, tunable policy (defensible to a methodologist); the reason is the model speaking plainly (kills the black-box objection). Both, together, are the wow.

**Files:**
- Modify: `config/materiality.yaml` (add `tiers`)
- Modify: `config/labels.yaml` (replace `priority_bands` with `tiers`)
- Modify: `backend/app/config/schema.py` (`MaterialityConfig`, `LabelsConfig`)
- Modify: `backend/app/services/scoring/materiality.py` (add `tier_for`, `primary_stakeholder`)
- Modify: `backend/app/models/signal.py` (add `why_it_matters`)
- Create: `backend/alembic/versions/<hash>_add_why_it_matters.py`
- Modify: `backend/agent/prompts/contextualize.md`, `backend/agent/nodes/contextualize.py`, `backend/app/services/agent_service.py`
- Modify: `backend/app/controllers/signals.py:70-112` (serializer)
- Test: `backend/../tests/test_scoring.py` (extend), `backend/../tests/test_api_reads.py` (extend)

**Interfaces:**
- Produces (backend):
  - `tier_for(total: float, config: AppConfig) -> str` returning `"act_on_it" | "worth_knowing" | "background"`.
  - `primary_stakeholder(scores: dict[str, float]) -> str` returning the persona with the max score (ties break `exec > product > sales`).
  - Signal JSON gains: `tier: str`, `tier_label: str`, `primary_stakeholder: str`, `why_it_matters: str`. `score` and `score_breakdown` are **removed from the payload** (kept internal).
- Consumed by: Tasks 3, 5, 7 (client reads `tier`, `tier_label`, `why_it_matters`, `primary_stakeholder`).

- [ ] **Step 1: Config.** Add to `config/materiality.yaml`:

```yaml
tiers:
  act_on_it: 60      # overall score at/above this → "Act on it"
  worth_knowing: 35  # at/above this → "Worth knowing"; below → "Background"
```

Replace the numeric bands in `config/labels.yaml` (`priority_bands:` block) with:

```yaml
tiers:
  act_on_it:     Act on it
  worth_knowing: Worth knowing
  background:    Background
```

- [ ] **Step 2: Schema.** In `backend/app/config/schema.py`, add `tiers: dict[str, float]` to `MaterialityConfig` and `tiers: dict[str, str]` to `LabelsConfig`; remove `priority_bands` from `LabelsConfig` (grep for `priority_bands` usage first — `PriorityBand` may be referenced by the coverage/kits code; if so, keep the class but drop the field from `LabelsConfig`).

- [ ] **Step 3: Write failing tests for the scorer.**

```python
# tests/test_scoring.py (add)
from app.services.scoring.materiality import tier_for, primary_stakeholder
from app.config.loader import load_config

def test_tier_bands():
    cfg = load_config()
    assert tier_for(75, cfg) == "act_on_it"
    assert tier_for(40, cfg) == "worth_knowing"
    assert tier_for(10, cfg) == "background"

def test_primary_stakeholder_is_argmax_with_exec_tiebreak():
    assert primary_stakeholder({"sales": 10, "product": 50, "exec": 50}) == "exec"
    assert primary_stakeholder({"sales": 30, "product": 10, "exec": 5}) == "sales"
```

- [ ] **Step 4: Implement in `materiality.py`.**

```python
_TIE_ORDER = {"exec": 3, "product": 2, "sales": 1}

def tier_for(total: float, config) -> str:
    t = config.materiality.tiers
    if total >= t["act_on_it"]:
        return "act_on_it"
    if total >= t["worth_knowing"]:
        return "worth_knowing"
    return "background"

def primary_stakeholder(scores: dict[str, float]) -> str:
    return max(scores, key=lambda p: (scores[p], _TIE_ORDER[p]))
```

- [ ] **Step 5: DB column.** Add to `backend/app/models/signal.py` `Signal`:

```python
why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Generate the migration: `cd backend && alembic revision -m "add why_it_matters" --autogenerate`, then review it adds exactly the one nullable column.

- [ ] **Step 6: LLM reason.** Append to `backend/agent/prompts/contextualize.md` a rule and schema field:

```
- `why_it_matters` is ONE plain sentence naming the JFrog consequence, at most 140
  characters, no numbers and no jargon. Pattern: "<what it does> to <JFrog area>".
  Example: "Directly targets Artifactory's SBOM story." If nothing material, say
  so plainly: "Background — no direct JFrog overlap."
```

In `backend/app/services/agent_service.py`, where the contextualization result is persisted onto the `Signal`, add `signal.why_it_matters = contextualization.get("why_it_matters")` alongside the existing `so_what_*` assignments (grep `so_what_sales` in that file to find the exact block).

- [ ] **Step 7: Serialize.** In `backend/app/controllers/signals.py` `_serialize_signal`, compute and add the new fields and remove the numeric ones:

```python
from app.services.scoring.materiality import tier_for, primary_stakeholder
# ...
scores = {
    "sales": float(signal.score_sales),
    "product": float(signal.score_product),
    "exec": float(signal.score_exec),
}
stakeholder = primary_stakeholder(scores)
overall = scores[stakeholder]
# in the returned dict: DROP "score" and "score_breakdown"; ADD:
    "tier": tier_for(overall, cfg),
    "tier_label": cfg.labels.tiers[tier_for(overall, cfg)],
    "primary_stakeholder": stakeholder,
    "why_it_matters": signal.why_it_matters or "",
```

Keep `so_what` per active persona exactly as-is (Divisions depends on it).

- [ ] **Step 8: Extend API read test** to assert a signal row has `tier in {act_on_it, worth_knowing, background}`, has `why_it_matters`, and has **no** `score` key. Run `cd backend && python -m pytest ../tests/test_scoring.py ../tests/test_api_reads.py -q`, verify pass, commit.

```bash
git add config/materiality.yaml config/labels.yaml backend/app/config/schema.py backend/app/services/scoring/materiality.py backend/app/models/signal.py backend/alembic/versions/ backend/agent/prompts/contextualize.md backend/app/services/agent_service.py backend/app/controllers/signals.py ../tests/test_scoring.py ../tests/test_api_reads.py
git commit -m "feat: hybrid tier + LLM reason; drop numeric score from signal payload"
```

---

### Task 3: Re-skin the card — tier badge + reason, no numbers

**Wow objective:** The card must answer "do I care?" and "why?" at a glance, with zero numeric noise. The colour and the tier word carry the verdict; the one-line reason carries the justification.

**Files:**
- Create: `client/src/components/TierBadge.tsx`
- Modify: `client/src/config/labels.ts` (tier labels + hues)
- Modify: `client/src/api/types.ts` (`Signal` gains `tier`, `tier_label`, `primary_stakeholder`, `why_it_matters`; remove `score`/`score_breakdown` reliance)
- Modify: `client/src/components/SignalCard.tsx` (swap `ScoreBadge` → `TierBadge`; render `why_it_matters`; delete the "Why this score" disclosure)
- Delete usage of: `client/src/components/primitives/ScoreBadge.tsx` (leave the file, remove imports)
- Test: `client/src/components/SignalCard.test.tsx`

**Interfaces:**
- Consumes: `Signal.tier`, `Signal.tier_label`, `Signal.why_it_matters`, `Signal.primary_stakeholder` (from Task 2).
- Produces: `<TierBadge tier={tier} label={label} />`.

- [ ] **Step 1: Types.** In `types.ts` add `export type Tier = "act_on_it" | "worth_knowing" | "background";` and to `Signal`: `tier: Tier; tier_label: string; primary_stakeholder: Persona; why_it_matters: string;`. Remove `score` and `score_breakdown` (or make optional and stop reading them).

- [ ] **Step 2: labels.ts** — add a tier→hue map (three calm, non-alarmist hues; Act on it = the strongest accent, Background = muted):

```ts
export const TIER_HUE: Record<Tier, string> = {
  act_on_it: "var(--tier-act)",
  worth_knowing: "var(--tier-worth)",
  background: "var(--tier-bg)",
};
```
Add those three tokens to the client's token CSS file (grep for `--sig-product` to find it).

- [ ] **Step 3: Failing test** — the card shows the tier label and the reason, and no digits appear.

```tsx
it("shows the tier verdict and one-line reason, with no numbers", () => {
  render(<SignalCard signal={{ ...fixture, tier: "act_on_it", tier_label: "Act on it",
    why_it_matters: "Directly targets Artifactory's SBOM story." }} persona="sales" />);
  expect(screen.getByText("Act on it")).toBeInTheDocument();
  expect(screen.getByText(/Artifactory's SBOM story/)).toBeInTheDocument();
  expect(screen.queryByTestId("score-badge")).toBeNull();
});
```

- [ ] **Step 4: TierBadge + SignalCard.** Create `TierBadge.tsx` (a coloured pill using `TIER_HUE`). In `SignalCard.tsx`: replace `<ScoreBadge value={signal.score} />` with `<TierBadge tier={signal.tier} label={signal.tier_label} />`; add a prominent `why_it_matters` line directly under the headline; delete the `<Disclosure label="Why this score">` block and its `ScoreBreakdownContent`. Keep the "How this was produced" trace disclosure (that is provenance, not a number).

- [ ] **Step 5: Run, pass, commit.**

```bash
git add client/src/components/TierBadge.tsx client/src/config/labels.ts client/src/api/types.ts client/src/components/SignalCard.tsx client/src/components/SignalCard.test.tsx
git commit -m "feat(client): tier verdict + reason on cards, remove numeric score UI"
```

---

### Task 4: Strip diffing from every surface

**Wow objective:** The promise is "what matters right now," not "what changed." Any "was → now," ⚠ changed flag, or "last changed" column contradicts the single-snapshot story and reintroduces the complexity we are removing. Cut it from the UX; leave the engine in the repo for the roadmap slide.

**Files:**
- Modify: `client/src/components/SignalCard.tsx` (remove `WasNow` + `signal.change` render)
- Modify: `client/src/components/ComparisonTable.tsx` (remove "Last changed" column + `changed_recently` ⚠)
- Modify: `backend/app/controllers/comparison.py` (stop emitting `last_changed_at`, `changed_recently`, `change`)
- Modify: `backend/app/controllers/signals.py` (stop emitting `change`)
- Modify: `client/src/api/types.ts` (`Signal.change` and `BattlecardRow.change`/`last_changed_at`/`changed_recently` → remove or optional)
- Test: `client/src/pages/comparison.test.tsx`, `backend/../tests/test_comparison.py`, `test_api_reads.py`

**Interfaces:**
- Produces: comparison rows without any change fields; signal rows without `change`.

- [ ] **Step 1: Failing tests** — assert the comparison payload has no `changed_recently`/`last_changed_at` and the table renders no "Last changed" header; assert the signal payload has no `change` key.

- [ ] **Step 2: Backend.** In `comparison.py` `list_comparison`, delete the `changed_recently`/`last_changed_at`/`change` keys and the `_change_for_claim` call (leave `_change_for_claim` defined but unused, or delete it). In `signals.py` `_serialize_signal`, remove `"change": breakdown.get("change")`.

- [ ] **Step 3: Client.** Remove the `WasNow` import and the `{signal.change ? <WasNow/> : null}` block from `SignalCard.tsx`. In `ComparisonTable.tsx` delete the fourth `<th>Last changed</th>`, its `<td>`, and the `changed_recently` ⚠ span.

- [ ] **Step 4: Run backend + client suites for these files, pass, commit.**

```bash
git commit -am "refactor: remove change-detection from all UI surfaces (single-snapshot)"
```

---

## Phase B — The two hero rooms (Tasks 5–6)

### Task 5: Today — one headline verdict + 3–5 ranked cards

**Wow objective:** The 90-second skim. The top of the page is a single generated sentence that tells the reader whether today needs them ("Quiet day, one thing worth your attention: …" or "Two items to act on today, led by: …"). Below it, at most five full-width cards ranked by tier. Scarcity is the wow — five things, not fifty. The KIT grid is retired.

**Files:**
- Create: `backend/app/services/today_brief.py`
- Modify: `backend/app/controllers/signals.py` (or a small `today.py` controller) to expose `GET /today`
- Modify: `backend/app/main.py` (register route)
- Modify: `client/src/pages/Today.tsx` (rebuild)
- Modify: `client/src/api/types.ts` (add `TodayBrief`), `client/src/api/client.ts`/`endpoints.ts`
- Test: `backend/../tests/test_today_brief.py`, `client/src/pages/today.test.tsx`

**Interfaces:**
- Produces (backend): `GET /today` → `{ "headline": str, "cards": Signal[] }` where `cards` are the top ≤5 active signals ordered by overall score desc, and `headline` is composed deterministically from the tier mix.
- `compose_headline(cards: list[dict]) -> str` in `today_brief.py`.

- [ ] **Step 1: Failing test for the composer** — three shapes of day:

```python
# tests/test_today_brief.py
from app.services.today_brief import compose_headline

def test_headline_quiet_day():
    assert "Quiet day" in compose_headline([{"tier": "background", "headline": "x"}])

def test_headline_one_act_item():
    cards = [{"tier": "act_on_it", "headline": "Sonatype claims 80% better malware data"}]
    h = compose_headline(cards)
    assert "one thing worth your attention" in h.lower()
    assert "Sonatype" in h

def test_headline_multiple_act_items():
    cards = [{"tier": "act_on_it", "headline": "A"}, {"tier": "act_on_it", "headline": "B"}]
    assert "act on" in compose_headline(cards).lower()
```

- [ ] **Step 2: Implement `today_brief.py`.**

```python
def compose_headline(cards: list[dict]) -> str:
    act = [c for c in cards if c["tier"] == "act_on_it"]
    if not act:
        lead = cards[0]["headline"] if cards else "nothing new of note"
        return f"Quiet day — one thing worth a look: {lead}."
    if len(act) == 1:
        return f"One thing worth your attention: {act[0]['headline']}."
    return f"{len(act)} items to act on today, led by: {act[0]['headline']}."
```

- [ ] **Step 3: `GET /today`** — reuse `list_signals` to get active signals ranked by overall score (add an internal ranked helper or sort the serialized items by the same score used for `primary_stakeholder`), take the top 5, and return `{headline: compose_headline(top), cards: top}`. Register in `main.py`.

- [ ] **Step 4: Rebuild `Today.tsx`** — fetch `GET /today`; render the headline in a prominent banner, then map `cards` to full-width `SignalCard`s (stacked, not a grid). Delete the `KitTile` grid and the `findLeadKey` logic. Keep `SignalCard` full-width by passing a `variant="wide"` or wrapping in a single-column flex.

- [ ] **Step 5: Client + backend tests, pass, commit.**

```bash
git commit -am "feat: Today is a headline verdict + up to five ranked cards"
```

---

### Task 6: Competitors — the JFrog-component grid

**Wow objective:** The reader sees JFrog's own product line down the side (Artifactory, Xray, Curation, AppTrust, Advanced Security, Runtime Security, AI/ML) and, across, where each rival stands against it — a positional map nobody handed them before. Click a cell to expand the sourced evidence. This is analysis, not a feed.

**Files:**
- Create: `config/jfrog_components.yaml`
- Create: `backend/app/services/comparison_matrix.py`
- Modify: `backend/app/config/schema.py` (`JfrogComponentsConfig`), `backend/app/config/loader.py`
- Modify: `backend/app/controllers/comparison.py` (add `list_comparison_matrix`) + `main.py` (route `GET /comparison/matrix`)
- Create: `client/src/components/ComparisonGrid.tsx`
- Modify: `client/src/pages/Comparison.tsx`, `client/src/api/types.ts`, `client/src/api/client.ts`
- Test: `backend/../tests/test_comparison_matrix.py`, `client/src/pages/comparison.test.tsx`

**Interfaces:**
- `config/jfrog_components.yaml` shape (each component owns one or more capability dimensions already used by `jfrog_positions.yaml`):

```yaml
components:
  - key: artifactory
    name: Artifactory
    dimensions: [package_format_support, deployment_model]
  - key: xray
    name: Xray
    dimensions: [malware_detection, vulnerability_scanning]
  - key: curation
    name: Curation
    dimensions: [policy_engine]
  - key: apptrust
    name: AppTrust
    dimensions: [sbom, build_provenance]
  - key: advanced_security
    name: Advanced Security
    dimensions: [runtime_security]
  - key: ai_ml
    name: AI / ML
    dimensions: [model_registry]
```

- Produces (backend): `GET /comparison/matrix` → 
```
{ "components": [ { "key": str, "name": str,
    "cells": [ { "competitor": str, "competitor_name": str,
                 "stance": "ahead" | "behind" | "comparable" | "no_claim",
                 "summary": str,               # one plain line
                 "jfrog_position": str,        # authored
                 "evidence": Evidence[] } ] } ],
  "competitors": [ { "slug": str, "name": str } ] }
```
`stance` is derived from whether a competitor claim exists for any of the component's dimensions and its origin (`no_claim` when absent). Keep it a plain word — no number.
- Consumed by: `ComparisonGrid.tsx`.

- [ ] **Step 1: Config + schema + loader.** Add `jfrog_components.yaml`, a `JfrogComponentsConfig` model (`components: list[Component]`), and load it in `loader.py` next to `jfrog_positions`.

- [ ] **Step 2: Failing test for the builder** — given a seeded competitor with a claim on `malware_detection`, the `xray` component row has a cell for that competitor with `stance != "no_claim"` and non-empty `evidence`.

- [ ] **Step 3: Implement `comparison_matrix.py`** — for each component, for each competitor entity (kind=competitor), gather claims whose `dimension in component.dimensions`, map to a cell (reuse `_evidence_for_claim` logic from `comparison.py`; factor it into a shared helper if convenient), set `jfrog_position` from `jfrog_positions.yaml` for the component's primary dimension, and `stance` = `no_claim` if no competitor claim else `comparable` (a richer stance model is a roadmap item — keep it honest and simple now). Add `list_comparison_matrix` in `comparison.py` and the route.

- [ ] **Step 4: `ComparisonGrid.tsx`** — render a table: first column = component name (+ JFrog position on click), one column per competitor, each cell shows the `stance` word + `summary`; clicking a cell expands a panel with the verbatim quote and the **linked** source (reuse the Task 1 anchor pattern). Horizontal scroll inside an `overflow-x:auto` wrapper (wide tables must not scroll the page — see Global Constraints on responsive tables in the client plan).

- [ ] **Step 5: Point `Comparison.tsx` at `/comparison/matrix`** and render `ComparisonGrid`. Keep the old per-competitor `ComparisonTable` only if a competitor profile drill-down is still wanted; otherwise retire it.

- [ ] **Step 6: Tests pass, commit.**

```bash
git commit -am "feat: Competitors room as a JFrog-component × competitor grid with sourced cells"
```

---

## Phase C — Signals & Industry (Tasks 7–8)

### Task 7: Signals room — intent, not change

**Wow objective:** A deliberate, denser room for someone digging in. It reads a job posting, a pricing page, a changelog as *intent* ("they are hiring a reachability-analysis engineer → roadmap direction") — with no historical comparison needed. Grouped by signal type.

**Files:**
- Create: `client/src/pages/Signals.tsx`
- Modify: `client/src/config/navigation.ts`, `client/src/app/routes.tsx`
- Modify: `client/src/api/client.ts` (reuse `getSignals`)
- Test: `client/src/pages/divisions.test.tsx` sibling or new `signals.test.tsx`

**Interfaces:**
- Consumes: `GET /signals` (existing), grouped client-side by `signal_type`, rendered with `SignalCard` (already de-numbered + de-diffed by Phase A).

- [ ] **Step 1: Failing test** — the page renders a section header per present signal type (using `signal_type_label`) and at least one card under it; no persona tabs (this is not Divisions).

- [ ] **Step 2: Implement `Signals.tsx`** — fetch `getSignals({})`, group items by `signal_type`, render a `SectionLabel` per group (Hiring signal, Pricing & packaging, Product release, …) followed by that group's `SignalCard`s. Add intro copy framing these as *intent*, and explicitly not "what changed."

- [ ] **Step 3: Wire nav + route** (folded into Task 10's IA change if executed together). Tests pass, commit.

```bash
git commit -am "feat: Signals room grouped by intent type"
```

---

### Task 8: Industry — stable themes with a JFrog-relevance line

**Wow objective:** The market on its own terms, clustered into a stable set of themes so the page does not reshuffle daily and lose the reader. Each theme tile is a one-line state of play; each theme page adds a synthesis paragraph and — the thing that keeps it intelligence, not a news reader — a "what this means for JFrog" section.

**Files:**
- Create: `config/themes.yaml`, `backend/app/services/industry_themes.py`
- Modify: `backend/app/controllers/industry.py`, `backend/app/main.py`
- Modify: `client/src/pages/Industry.tsx`; Create `client/src/pages/ThemePage.tsx`
- Modify: `client/src/api/types.ts`, `client/src/api/client.ts`, `client/src/app/routes.tsx`
- Test: `backend/../tests/test_industry_themes.py`, `client/src/pages/grids.test.tsx`

**Interfaces:**
- `config/themes.yaml`:

```yaml
themes:
  - key: supply_chain_attacks
    label: Supply-chain attacks & CVEs
    match: { signal_types: [security_trust], keywords: [cve, malware, compromise, exploit] }
    jfrog_relevance: "Raises demand for provenance and blocking at the gate — Curation and Xray."
  - key: regulation
    label: Regulation & compliance
    match: { signal_types: [market_regulatory], keywords: [cra, sbom, mandate, executive order] }
    jfrog_relevance: "SBOM mandates map directly to AppTrust's evidence story."
  - key: funding_ma
    label: Funding & acquisitions
    match: { signal_types: [corporate_financial], keywords: [acquires, funding, raises, series] }
    jfrog_relevance: "Consolidation reshapes the competitive set."
  - key: ai_mlops
    label: AI / MLOps & model registries
    match: { signal_types: [product_capability], keywords: [model, mlops, registry, llm] }
    jfrog_relevance: "Validates JFrog ML / AI Catalog as the next artifact frontier."
```

- Produces (backend): `GET /industry/themes` → `[{ key, label, count, state_of_play, jfrog_relevance }]`; `GET /industry/themes/{key}` → `{ label, synthesis, jfrog_relevance, items: IndustryItem[] }`.
- `assign_theme(item, themes) -> str | None` in `industry_themes.py` — deterministic: first theme whose `signal_type` matches AND (no keywords, or a keyword hits the headline/body). Unmatched items fall to an `other` bucket.

- [ ] **Step 1: Failing test** — an item with `signal_type=market_regulatory` and "SBOM" in the headline assigns to `regulation`; theme list returns stable keys with counts.

- [ ] **Step 2: Implement `industry_themes.py`** (`assign_theme`, `list_themes`, `theme_detail`) + schema for `themes.yaml` + loader. `state_of_play` is a one-line template: `f"{count} items — {label}"` (the LLM-written synthesis on the detail page is optional; keep the tile deterministic and stable).

- [ ] **Step 3: Endpoints** in `industry.py` + `main.py`.

- [ ] **Step 4: Client** — `Industry.tsx` becomes a grid of theme tiles (label · count · one-line state of play); clicking routes to `ThemePage.tsx` which shows the synthesis, the **JFrog relevance** section, and the underlying `IndustryCard`s (with linked sources from Task 1). Keep the theme set stable across renders (order by `themes.yaml`).

- [ ] **Step 5: Tests pass, commit.**

```bash
git commit -am "feat: Industry clustered into stable themes with JFrog-relevance"
```

---

## Phase D — Intention-based config (Task 9)

### Task 9: Settings without arithmetic

**Wow objective:** A non-technical analyst tunes the system by stating *intent* — "also watch this competitor," "flag anything mentioning SLSA," "when scoring security items, lead on posture" — never by dragging a numeric weight. They understand intentions, not coefficients.

**Files:**
- Create: `config/instructions.yaml`
- Modify: `backend/app/controllers/config.py` (competitors + instructions read/write), `backend/app/main.py`
- Modify: `backend/agent/prompts/extract.md`, `contextualize.md` (inject instructions)
- Modify: `backend/app/services/agent_service.py` (pass instructions into the prompt context)
- Create: `client/src/components/CompetitorEditor.tsx`, `client/src/components/InstructionsEditor.tsx`
- Modify: `client/src/pages/Settings.tsx` (remove `WeightEditor`; keep `WatchlistEditor`)
- Test: `backend/../tests/test_api_writes.py`, `client/src/pages/settings.test.tsx`

**Interfaces:**
- `config/instructions.yaml`: `{ instructions: list[str] }`.
- Produces (backend): `GET/PUT /config/instructions` → `{ config_version, instructions: string[] }`; `GET/PUT /config/competitors` → `{ config_version, competitors: [{ slug, name }] }` (writing appends an entity of kind `competitor`; do **not** auto-scrape — a new competitor with no source is a coverage gap, which the existing coverage matrix already surfaces).
- Instructions are appended to the `extract`/`contextualize` prompts verbatim under an "Analyst instructions" heading; they are guidance, never override the untrusted-content rules already in `extract.md`.

- [ ] **Step 1: Failing tests** — `PUT /config/instructions` persists and `GET` returns them; the extract prompt builder includes an instruction string when present. (For the write test, follow the `test_api_writes.py` pattern that stubs the job.)

- [ ] **Step 2: Backend** — add the two config files/endpoints mirroring the existing `watchlist` read/write in `config.py`. In `agent_service.py`, load `config.instructions` and format them into the prompt text the nodes receive (the nodes already call `deps.prompt("extract")`; extend the prompt assembly to append instructions).

- [ ] **Step 3: Client** — `CompetitorEditor` (add/remove competitor chips → `PUT /config/competitors`) and `InstructionsEditor` (a list of free-text lines → `PUT /config/instructions`), both modelled on `WatchlistEditor.tsx`. Remove `WeightEditor` from `Settings.tsx` and its route/import. Keep `WatchlistEditor`, `SourceTable`, `CoverageMatrix`.

- [ ] **Step 4: Tests pass, commit.**

```bash
git commit -am "feat: intention-based Settings (competitors, keywords, instructions); remove numeric weights"
```

---

## Phase E — Information architecture (Task 10)

### Task 10: Collapse the navigation

**Wow objective:** Memorable and complete — the reader never wonders which room to open. Four daily rooms plus Divisions, Email, Ask, Settings; the change-detection pages leave the surface (their code stays for the roadmap story).

**Files:**
- Modify: `client/src/config/navigation.ts`, `client/src/app/routes.tsx`
- Test: `client/src/config/navigation.test.ts`, `client/src/app/AppShell.test.tsx`

- [ ] **Step 1: Failing test** — `NAVIGATION` contains Today, Competitors, Signals, Industry, Divisions, Ask, Settings, Email Digest, and does **not** contain Trajectory or Competitors→Us as primary items.

- [ ] **Step 2: Rewrite `NAVIGATION`:**

```ts
export const NAVIGATION: NavItem[] = [
  { path: "/",           label: "Today",       group: "daily",     icon: "list",    primary: true },
  { path: "/comparison", label: "Competitors", group: "daily",     icon: "chart",   primary: true },
  { path: "/signals",    label: "Signals",     group: "daily",     icon: "activity",primary: true },
  { path: "/industry",   label: "Industry",    group: "daily",     icon: "globe",   primary: true },
  { path: "/divisions",  label: "Divisions",   group: "reference", icon: "users",   primary: true },
  { path: "/ask",        label: "Ask",         group: "tools",     icon: "message" },
  { path: "/settings",   label: "Settings",    group: "tools",     icon: "gear" },
  { path: "/digest",     label: "Email Digest",group: "tools",     icon: "mail" },
];
```

- [ ] **Step 3: Routes** — keep `Trajectory`, `AboutUs`, `ClaimTimeline` route components importable (do not delete files) but remove them from the sidebar. Update `routes.tsx` to add `/signals` and the theme routes; leave `/trajectory` reachable by URL for the roadmap demo.

- [ ] **Step 4: Tests pass, commit.**

```bash
git commit -am "refactor(client): verdict-first navigation; bench change-detection pages"
```

---

## Self-review — spec coverage

| Locked decision | Task(s) |
|---|---|
| 1 — Divisions / per-persona so-what kept | Task 2 keeps `so_what_{persona}`; Task 10 keeps Divisions |
| 2 — JFrog-component grid | Task 6 |
| 3 — source link + date everywhere | Task 1 (+ every new card reuses the anchor pattern) |
| 4 — Email Digest kept | Task 10 keeps `/digest` |
| 5 — intention-based config | Task 9 |
| 6 — hybrid tier + reason | Tasks 2–3 |
| 7 — Ask skeleton | untouched (explicitly out of scope) |
| 8 — no diffing / single snapshot | Task 4 (+ Task 10 benches diffing pages) |
| Vision §1 no numbers/jargon | Tasks 2–4 |
| Vision §4 Today shape | Task 5 |
| Vision §4 Signals room | Task 7 |
| Vision §4 Industry themes | Task 8 |
| Vision §5 three plain tiers | Task 2 |

**Known follow-ups (not in this plan, state honestly in the demo):** LLM-authored theme synthesis paragraphs (Task 8 ships deterministic tiles); a richer `stance` model for the comparison grid (Task 6 ships `no_claim`/`comparable`); the live Ask chat (skeleton only). Change-detection, alerting, and per-run deltas remain in the repo as the roadmap story, off the primary surface.

---


