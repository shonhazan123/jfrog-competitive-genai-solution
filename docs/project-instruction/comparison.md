# Comparison — verdict-first competitor matrix

The primary Competitors surface is a **transposed capability matrix**: competitors
(rows) × buyer-facing capability dimensions (columns), each cell a stance backed by a
source. Click a competitor row to open the full per-dimension assessment detail page.
No numbers, no `was → now` diffing.

## Research agent

- Worker entry: `run_comparison()` in `app/services/research/comparison_agent.py`
- Graph deps: `agent/graphs/research/comparison/deps.py` — per-cell search + stance gate
- Config: `config/comparison_dimensions.yaml` (five dimensions with `jfrog_position` yardsticks)
- Competitor allowlist: `config/competitors.yaml` (github, sonatype, snyk, aqua, checkmarx)
- Persist: upsert `Claim` (subject=jfrog, asserting=competitor, `dimension`, `stance`, `claim_text`) + `Evidence` + `index_finding`; skip `stance == "none"`
- Registry-less rivals correctly resolve to `none` for dimensions they do not publicly claim
- **Citation URLs:** web-search findings are stored via `record_finding()` under a synthetic
  `comparison_research` source (`internal://…`), but the fetched page URL lives on
  `RawCapture.blob_path`. Serializers (`evidence_from_capture`) expose that real URL in
  `evidence.source_url` / `citation.source_url` (label = page hostname, e.g. `sonatype.com`).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/comparison/matrix` | Dimension × competitor stance grid (primary surface) |
| GET | `/comparison?competitor={slug}` | Legacy claim-by-claim list (benched `about-us`/`trajectory` only) |

## Matrix build (`app.services.comparison_matrix.build_comparison_matrix`)

- **Columns** come from `config/comparison_dimensions.yaml` — five buyer-facing dimensions
  (`artifact_management`, `sca_sbom`, `container_security`, `cicd_integration`,
  `developer_experience`) each with `label`, `probe_keywords`, and `jfrog_position`.
- **Rows** are the allowlisted competitors from `load_competitors()` (five rivals).
- For each dimension × competitor, lookup `Claim` by `(asserting_entity_id=competitor,
  subject_entity_id=jfrog, dimension=dim.key)`.
- `evidence_for_claim` attaches the first linked evidence (quote + source) when a claim exists.

Return shape: `{ "dimensions": [{ key, name, cells: [Cell] }], "competitors": [{ slug, name }] }`.

Legacy `config/jfrog_components.yaml` was removed; the grid no longer uses JFrog product rows.

## Client presentation (transposed view)

The API returns **dimension × competitor**. The client transposes this to
**competitor × capability-dimension** for the Figma-aligned UI.

- **Type:** `ComparisonMatrix` uses `dimensions` (not legacy `components`) plus
  `competitors`.
- **Stance values** from the API: `strong | moderate | weak | none`
- `none` means no public claim — cell renders neutral/empty; `summary` reads
  "No public claim on record."
- `comparisonPresentation.ts` maps dimension keys to labels; `stance` is used
  directly as the strength indicator (no ahead/comparable/behind mapping).
- Fixture: `client/src/fixtures/comparison_matrix.json` — 5 dimensions × 5
  competitors with a mix of stance values.

## Cell shape

```json
{ "competitor", "competitor_name", "stance", "summary", "jfrog_position", "evidence": [Evidence] }
```

Change-detection fields (`change`, `changed_recently`, `last_changed_at`) were
removed from `/comparison` in the verdict-first redesign and must not reappear on
any consumer surface.

## Testids

| testid | element |
|---|---|
| `table-scroll` | horizontal scroll container |
| `competitor-row-{slug}` | clickable competitor row |
| `matrix-cell-{slug}-{componentKey}` | transposed grid cell (`componentKey` = dimension key, e.g. `sca_sbom`) |
| `competitor-detail` | detail page root |
| `dimension-card-{componentKey}` | per-dimension assessment card on detail |
| `evidence-link-{componentKey}` | sourced evidence link on detail |
