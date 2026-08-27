# Comparison — verdict-first competitor matrix

The primary Competitors surface is a **single-snapshot matrix**: JFrog components
(rows) × competitors (columns), each cell a plain stance backed by a source. No
numbers, no `was → now` diffing.

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

## Cell shape (no grade, no diff)

```json
{ "competitor", "competitor_name", "stance", "summary", "jfrog_position", "evidence": [Evidence] }
```

`stance` is one of:

| stance | meaning |
|---|---|
| `comparable` | The competitor has a public claim on this component (shown with its evidence) |
| `no_claim` | No public claim found — `summary` reads "No public claim on record." |

Return shape: `{ "components": [{ key, name, cells: [Cell] }], "competitors": [{ slug, name }] }`.

Change-detection fields (`change`, `changed_recently`, `last_changed_at`) were
removed from `/comparison` in the verdict-first redesign and must not reappear on
any consumer surface.
