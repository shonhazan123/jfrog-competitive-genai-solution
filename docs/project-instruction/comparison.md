# Comparison — verdict-first competitor matrix

The primary Competitors surface is a **transposed capability matrix**: competitors
(rows) × JFrog capability dimensions (columns), each cell a plain stance backed by a
source. Click a competitor row to open the full per-dimension assessment detail page.
No numbers, no `was → now` diffing.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/comparison/matrix` | Component × competitor stance grid (primary surface) |
| GET | `/comparison?competitor={slug}` | Legacy claim-by-claim list (benched `about-us`/`trajectory` only) |

## Matrix build (`app.services.comparison_matrix.build_comparison_matrix`)

- **Rows** come from `config/jfrog_components.yaml` — each component has `key`,
  `name`, and `dimensions` (the claim dimensions it covers). This config is the
  source of truth for which JFrog capabilities the grid compares.
- **Columns** are every `Entity` with `kind == "competitor"`, ordered by `slug`
  (`competitors: [{ slug, name }]`).
- For each component × competitor, `_claim_for_component` finds the competitor's
  first claim on any of the component's dimensions. The JFrog side is the
  authored `jfrog_position` text for the component's primary dimension (from
  `config/jfrog_positions.yaml`), so JFrog cells are never graded.
- `evidence_for_claim` attaches the first linked evidence (quote + source) so the
  cell's claim is clickable.

## Client presentation (transposed view)

The API returns **JFrog-component × competitor**. The client transposes this to
**competitor × capability-dimension** for the Figma-aligned UI:

- **Columns** = each `components[]` entry from the matrix, labelled via
  `client/src/utils/comparisonPresentation.ts` `DIMENSION_LABELS` (Figma-aligned
  names where possible, e.g. `artifactory` → "Artifact Management").
- **Rows** = each `competitors[]` entry; row click sets `selectedCompetitor` and
  renders `CompetitorDetail` (in-component state, no route change).
- **Stance → strength** (grid dot/bar + detail cards):
  - `ahead` → Strong (`--brand-jfrog`)
  - `comparable` → Moderate (`--tier-worth`)
  - `behind` → Weak (`--tier-act`)
  - `no_claim` → None (`--tier-bg`)
- **Threat chip** — not in the API. When the competitor has at least one public
  claim, a deterministic **derived** threat is shown from stance counts (`ahead`
  and `comparable` cells with evidence). Label includes "· derived". Omitted when
  no claims exist (e.g. Harbor in the fixture).
- **Category** — not in the API; omitted on the detail page.

## Cell shape (no grade, no diff)

```json
{ "competitor", "competitor_name", "stance", "summary", "jfrog_position", "evidence": [Evidence] }
```

`stance` is one of:

| stance | meaning |
|---|---|
| `ahead` | Competitor claims advantage vs JFrog on this component |
| `behind` | Competitor claims disadvantage vs JFrog |
| `comparable` | The competitor has a public claim on this component (shown with its evidence) |
| `no_claim` | No public claim found — `summary` reads "No public claim on record." |

Return shape: `{ "components": [{ key, name, cells: [Cell] }], "competitors": [{ slug, name }] }`.

Change-detection fields (`change`, `changed_recently`, `last_changed_at`) were
removed from `/comparison` in the verdict-first redesign and must not reappear on
any consumer surface.

## Testids

| testid | element |
|---|---|
| `table-scroll` | horizontal scroll container |
| `competitor-row-{slug}` | clickable competitor row |
| `matrix-cell-{slug}-{componentKey}` | transposed grid cell |
| `competitor-detail` | detail page root |
| `dimension-card-{componentKey}` | per-dimension assessment card on detail |
| `evidence-link-{componentKey}` | sourced evidence link on detail |
