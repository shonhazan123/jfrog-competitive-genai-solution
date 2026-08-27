# Plan — Match the client UI to the `jforg_design` Figma export

**Date:** 2026-08-27
**Status:** Proposed (design/refactor plan, not yet executed)
**Scope:** Restyle and re-flow the existing `client/` React app so its UX/UI matches the
Figma export at `../jforg_design`, with two deliberate deviations and one font swap.

---

## 1. Goal

Reproduce the Figma design's **layout, information architecture, and interaction flows** in
our existing `client/` app — *without* adopting its stack (Tailwind + hardcoded hex + mock
`data.ts`). We keep our token system, react-router, react-query, and live API wiring; we
change how screens look and flow.

Two intentional deviations from the Figma source:

1. **Colour** — the Figma design is near-black dark (`#07090d`). We ship **light + vibrant**
   instead. Our client is *already* light (`--bg:#FBFBFD`); the work is to raise saturation
   and adopt Figma's editorial structure, not to invert a dark theme.
2. **Today cards** — Figma stacks them one-per-row down a narrow 768px column. We render
   them as a **grid that uses most of the page width**.

One adoption from Figma:

3. **Fonts** — take Figma's type: **Fraunces** (display serif), **Outfit** (sans), **DM Mono**
   (mono labels).

Two flows to copy **exactly** from Figma (called out by the requester):

- The **Competitors comparison grid** → click a row → the **expanded "logic" detail page**
  (per-dimension capability assessment).
- The general **click-to-expand** pattern behind sections (Signals intent-read accordion,
  Industry theme → detail page).

---

## 2. Decision record

| Question | Decision |
|---|---|
| Where does this live? | **In-place refactor of `client/`.** Not a standalone copy. |
| Data source | **Keep live API + fixtures** as-is. This is a UI/UX layer change; endpoints unchanged. |
| Colour direction | **Light + vibrant** (white/near-white base, saturated accent hues). |
| Fonts | **Adopt Figma's** — Fraunces / Outfit / DM Mono. |
| Styling engine | **Keep our CSS-token + inline-style system.** Do **not** import Tailwind. Map Figma's utilities onto our tokens. |

**Why keep the token system rather than port Figma's Tailwind:** our `tokens.css` already
encodes a deliberate 3-system colour model (hue = signal type, weight = materiality, form =
grade) plus a full light/dark palette. Figma's inline `bg-[#0c0f17]` hexes are a design
snapshot, not a system. Porting Tailwind would throw away that model and break every
`*.css` + `data-testid`-based test. We translate Figma's *look* into our *tokens*.

---

## 3. Global foundation (do first — everything else depends on it)

### 3.1 Fonts
- Add to `client/index.html` `<head>` (or top of `styles/base.css` via `@import`):
  - `Fraunces` (opsz, ital, wght 300/400/600)
  - `Outfit` (300–700)
  - `DM Mono` (300/400/500, ital)
- Repoint the three font tokens in `styles/tokens.css`:
  - `--font-sans: 'Outfit', system-ui, sans-serif;`
  - `--font-serif: 'Fraunces', Georgia, serif;` (Figma calls this `--font-display`)
  - `--font-mono: 'DM Mono', ui-monospace, monospace;`
- Add a `.font-display` helper and a `.mono-label` helper (uppercase, tracked, DM Mono) —
  these are used constantly in Figma for the small eyebrow labels ("POSITIONAL MAP",
  "PULL LAYER", date/source meta).

### 3.2 Palette — raise vibrancy, keep the model
Our light palette is calm-by-design; Figma reads more colourful because it leans on a few
saturated accents against a dark ground. To get "vibrant on light":

- Keep the existing `--sig-*` hues (they're already vivid: indigo/red/amber/violet/teal…).
- **Map Figma's tier colours onto our tier tokens** so tier reads as colour on Today/Signals:
  - `act-on-it` → amber (`--tier-act`; Figma uses `#f59e0b`)
  - `worth-knowing` → blue (`--tier-worth`; Figma `#60a5fa`)
  - `background` → muted slate (`--tier-bg`)
  - *(Note: our current `--tier-act` is blue `#2B59FF`. Figma anchors "act on it" to amber.
    Decide: keep our blue, or adopt Figma's amber. Recommendation: adopt amber for act-on-it
    so urgency reads warm, matching Figma. This is a token flip, one line.)*
- Add tinted **surface washes per tier/theme** (soft amber/blue/violet card backgrounds) so
  sections read colourful, matching the "Light + vibrant" choice. Use the existing
  `--*-wash` tokens; introduce `--tier-act-wash`, `--tier-worth-wash`.
- JFrog brand green (`#38c172` in Figma logo/accents) → add `--brand-jfrog` token; use for
  the logo block and the "JFrog relevance" callout on Industry detail.

### 3.3 App shell & navigation
Figma chrome vs ours:

| Figma | Current | Action |
|---|---|---|
| 220px sidebar, logo block top, 5 nav items, "Updated 2h ago" footer | 248px sidebar, 8 items in 3 groups (Daily/Reference/Tools), bottom bar on mobile | Restyle `Sidebar` to Figma look; add logo block + footer meta from `StatusStrip` data. |
| Mobile: slide-in overlay + hamburger | Mobile: fixed bottom bar | **Keep our bottom bar** (better mobile pattern) OR adopt Figma overlay. Recommend keep bottom bar; it already passes `responsive.test.tsx`. |
| Active item: green tint + green text + amber dot on "Today" | Active: `--accent-wash` + accent text | Restyle active state to brand-green tint; keep our token approach. |
| 5 rooms only | 8 items (extra: Divisions, Settings, Email Digest) | See §5 IA reconciliation — do **not** delete our extra rooms; fold them under a group. |

The Figma `StatusStrip`-equivalent ("Updated 2h ago · Aug 27, 2026 · 14 sources") maps
directly to our existing run-status data — reuse `StatusStrip`/`run_status` in the sidebar
footer.

---

## 4. Per-screen mapping

### 4.1 Today  — *(includes required change #2: grid)*
**Current:** `page-heading` "Today" + a headline `<p>` + a **vertical flex column** of full
`SignalCard`s (each with Confirm/Reject/Edit/Mute actions + trace disclosure).

**Figma target:**
- Eyebrow meta row: `Wednesday · Aug 27, 2026 · Daily Brief` (DM Mono, dim).
- **Verdict blockquote** — big Fraunces italic, amber left-rule, with a tally strip below
  (`2 act on it · 1 worth knowing · 2 background · N signals · 14 sources`).
- Divider, then ranked cards `#1…#5`, each: rank + tier dot/label, competitor eyebrow,
  bold headline, "so what" paragraph, `↳ tier reason` line, audience tags + area tags,
  source label.

**Changes:**
- Replace the plain headline `<p>` with the **verdict block** (Fraunces italic + tally).
  Source the verdict text from the Today brief `headline`; source the tally from card tiers.
- **Convert the card column to a responsive grid** using most of the width:
  `display:grid; grid-template-columns: repeat(auto-fill, minmax(380px,1fr)); gap:var(--sp-5)`
  and **widen the page** — raise/remove the `--content-max: 900px` clamp on Today so the grid
  spans the main area (Figma clamps to a narrow reading column; we deliberately do **not**).
- Introduce a **compact `IntelCard`** variant (Figma-style: rank, tier border, so-what,
  reason, audience/area tags) for the Today grid. The heavy `SignalCard` (actions + trace)
  stays for the Signals workflow; Today gets the lean read-only card. Keep `data-testid`s
  (`today-headline`, `signal-card`, `so-what`) so `today.test.tsx` keeps passing — the
  headline testid moves onto the verdict block.
- Tier colour drives the card's left border + dot + reason colour.

**Audience/area tags:** Figma shows `Sales/Product/Exec/Marketing` + `Artifactory/Xray/…`
chips. Our data has `primary_stakeholder` + entity/area. Map stakeholder → audience chip;
map JFrog area (if present) → area chip. If area isn't in the payload, omit gracefully.

### 4.2 Competitors  — *(required flow #1: grid → expanded logic page)*
**Current:** a `<table>` (JFrog components down rows, competitors across columns). **Two**
inline expands: click component name → shows JFrog position inline; click a cell → shows
evidence quote inline. No detail page.

**Figma target (copy exactly):**
- Landing = a **matrix grid**: **competitors down the rows, 5 capability dimensions across
  the columns** (`Artifact Management, SCA/SBOM, Container Security, CI/CD, Developer
  Experience`). Each cell = a **strength dot + label** (Strong/Moderate/Weak/None) + a short
  position line + a strength bar. Threat chip (High/Med/Low) on the competitor cell.
- Click a **row** → the **detail "logic" page**: back link, competitor name + category +
  threat chip, summary paragraph, then **per-dimension assessment cards** — each with a
  strength bar, position label, and the sourced evidence line.

**Changes / the real work here — axis transposition + data shape:**
- Figma's axis is **competitor × capability-dimension**. Ours is **JFrog-component ×
  competitor**, and our cell carries `stance/summary/evidence` + `jfrog_position`. These are
  **not the same matrix.** Two options:
  1. **(Recommended)** Build the Figma view as a **new presentation** over the existing
     `getComparisonMatrix()` data: transpose to competitor-rows, and derive the 5 dimensions
     from our component set (or add a `capability_dimension` grouping server-side later).
     The per-cell `stance` → strength label; `summary` → position line; evidence → detail.
  2. Add a backend `capability` field and a per-competitor summary. Larger; defer.
- Replace the **two-level inline expand** with Figma's **row → detail page** flow. This is a
  behaviour change: `ComparisonGrid` currently uses `expandedCell`/`expandedComponent` state;
  the new flow uses a `selectedCompetitor` state (like Figma's `Competitors.tsx`) or a
  nested route `/comparison/:slug`. **Recommendation: in-component state** (matches Figma
  exactly, no router change) — mirror Figma's `if (selected) return <CompetitorDetail/>`.
- ⚠️ **Test impact:** `comparison.test.tsx` + `grids.test.tsx` assert the current
  `matrix-cell-*`, `component-row-*`, `cell-evidence-*` testids and inline-expand behaviour.
  Transposing + moving to a detail page **will rewrite these tests.** Budget for it. Preserve
  a `matrix-cell-*` testid on the new cells and add `competitor-row-*` + a
  `competitor-detail` testid for the logic page.

### 4.3 Signals  — *(expand-in-place flow)*
**Current:** `SignalCard`s (rich, with actions + trace disclosure).

**Figma target:** signals **grouped by signal type** (Hiring/Pricing/Changelog/Docs/Funding)
with a **filter chip bar** (type + count), and each row is a **collapsed one-liner that
expands in place** to reveal the "intent read" + tier reason + audience tags.

**Changes:**
- Add the **type filter bar** (we already have a `FilterChips` primitive — reuse it).
- Add **group-by-type sections** with the small mono type header + count + rule (Figma
  pattern).
- Add a **collapsed→expanded accordion** row variant. We have a `Disclosure` primitive;
  either extend it or add an `expandedId` accordion like Figma's `Signals.tsx`.
- Reframe the expanded body around **"Intent read"** (Figma's framing) — this maps to our
  `so_what`/`why_it_matters`. Keep our evidence/source line.
- Our nine `signal_type`s (product_capability, positioning_messaging, … talent_org) are
  richer than Figma's five. **Keep all nine**; the filter bar just lists what's present.
- ⚠️ `signals.test.tsx` asserts card structure; grouping + accordion will touch it.

### 4.4 Industry  — *(tile → detail page flow)*
**Current:** theme tiles in a grid (`auto-fill minmax(420px)`) → **routed** `Link` to
`/industry/:key` detail. **This already matches Figma's flow.** ✅

**Figma target:** 2-column theme tiles (accent rule, title, clipped state-of-play, area
chips, item count + arrow) → detail page (accent rule, title, item-count/updated meta,
**State of Play** section, green **JFrog Relevance** callout box with area chips, **Source
Items** list with `↳ relevance line` + source/date).

**Changes:**
- Restyle `ThemeTile` to Figma (accent bar per theme, item count badge, arrow affordance).
- Restyle the detail route (`ThemePage.tsx`) to Figma: add the **green "JFrog Relevance"
  callout** (brand-green wash) and the `↳ relevance line` on each source item.
- Keep the routed flow (`/industry/:key`) — no need to switch to in-component state; it's a
  cleaner pattern than Figma's local state and already tested.
- Give each theme a stable accent hue (Figma: violet/blue/amber/green per theme key).

### 4.5 Ask  — *(cited chat)*
**Current:** `Ask.tsx` + `AskTranscript`. Figma: header eyebrow "PULL LAYER", suggested
questions (numbered, empty-state), user/assistant bubbles, **green citation badges**,
bouncing-dots loader, textarea with send button, "Enter to send · Shift+Enter" hint.

**Changes:** mostly cosmetic — restyle to Figma (suggested-question list, citation badge
style, loader, input chrome). Our Ask is already API-backed with citations; keep that.
Adopt the empty-state suggested-questions block and the green `CitationBadge` look.

---

## 5. Navigation / IA reconciliation

Figma has 5 rooms; we have 8 nav items (+ hidden pages: Trajectory, StyleGuide, AboutUs,
ThemePage). **Do not delete our extra rooms to match Figma.** Plan:

- Primary group mirrors Figma's five: **Today, Competitors, Signals, Industry, Ask.**
- Keep **Divisions, Settings, Email Digest** under a secondary "Tools/Reference" group in the
  sidebar (Figma has no equivalent, but removing working features to match a mock is wrong).
- Restyle nav items to Figma's look; keep our `navigation.ts` IA-as-data approach (regrouping
  never touches JSX — good, keep it).

---

## 6. Staged execution (with checkpoints)

Each stage is independently shippable and leaves tests green before moving on.

1. **Foundation** — fonts + palette vibrancy + tier-colour flip + font/token helpers.
   *Checkpoint:* app renders in new type/colour; no layout change yet; full test suite green.
2. **Shell & nav** — sidebar logo block, Figma active states, footer run-meta, mono eyebrow
   labels. *Checkpoint:* `responsive.test.tsx`, `AppShell.test.tsx` green.
3. **Today → verdict + grid** (required change #2). New lean `IntelCard`, verdict block,
   widened grid. *Checkpoint:* `today.test.tsx` updated + green.
4. **Signals** — filter bar + group-by-type + accordion intent-read.
   *Checkpoint:* `signals.test.tsx` updated + green.
5. **Industry** — tile + detail restyle + JFrog-relevance callout.
   *Checkpoint:* `industry`/`ThemePage` tests green.
6. **Competitors** (required flow #1, biggest) — transpose to competitor×dimension grid +
   row→detail logic page. *Checkpoint:* rewritten `comparison.test.tsx`/`grids.test.tsx`
   green.
7. **Ask** — cosmetic restyle + suggested-questions empty state + citation badges.
8. **Polish pass** — spacing/hover/transitions against Figma side-by-side; `StyleGuide.tsx`
   updated to the new system.

---

## 7. Risks & watch-items

- **Comparison axis transposition (§4.2)** is the one place data shape and Figma flow
  genuinely disagree. It's the highest-effort, highest-test-churn stage. Consider a small
  backend `capability_dimension` grouping if the client-side transpose gets ugly.
- **Test churn:** Today, Signals, Comparison tests assert current DOM/testids. Migrate
  testids deliberately; don't silently drop them.
- **Google Fonts network dependency:** three `@import`s add a load; self-host later if it
  matters for the demo. (No CSP issue — this is the app, not an Artifact.)
- **"Vibrant" vs the calm 3-system model:** don't let per-tier washes fight the signal-hue
  system on Signals cards. Tier drives Today/Signals borders; signal-hue stays on the
  detailed cards. Keep the two systems on separate surfaces.
- **Don't regress content honesty:** the Figma mock's richness is *fabricated* (see the
  companion analysis). Matching its *look* is the goal; do not add mock data to make our real
  (sparser) output look as full as the mock.

## 8. Out of scope
- Backend/collection changes (covered separately; the real coverage gap is a collection
  problem, not a UI one).
- Wiring new endpoints. This plan reshapes presentation over existing APIs only.
- The dark theme (we ship light+vibrant; the dark tokens stay in `tokens.css` untouched).
