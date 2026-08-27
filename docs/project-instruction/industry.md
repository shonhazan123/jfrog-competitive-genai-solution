# Industry lane — stable themes

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/industry` | Paginated industry signal feed (`items` / `total` / `cursor`) |
| GET | `/industry/themes` | Stable theme tiles ordered by `config/themes.yaml` |
| GET | `/industry/themes/{key}` | Theme detail with synthesis, JFrog relevance, and grouped items |

## Theme assignment

- Config: `config/themes.yaml` (loaded directly by `app.services.industry_themes`, not via `AppConfig`).
- `assign_theme(item, themes)` is deterministic: first theme whose `signal_type` is in `match.signal_types` and (no keywords, or a keyword substring hits headline/body case-insensitively).
- Unmatched active industry signals bucket under `other` (only present in list when count > 0).

## Response shapes

**`GET /industry/themes`** — JSON array:

```json
[{ "key", "label", "count", "state_of_play", "jfrog_relevance" }]
```

`state_of_play` is `"{count} items — {label}"` (deterministic, no LLM).

**`GET /industry/themes/{key}`**:

```json
{ "label", "synthesis", "jfrog_relevance", "items": [IndustryItem] }
```

`synthesis` is currently deterministic (`"{n} items grouped under {label}."`); LLM synthesis is a follow-up.

`items` use the same dict shape as `GET /industry` rows (including linked `evidence`).

## Client presentation (Stage 5 — Figma match)

- **`/industry`** — `Industry.tsx` renders a 2-column theme grid (`ThemeTile`) with accent
  bar (hue derived from `theme.key` via `config/themeAccent.ts`), `.font-display` title,
  CSS-clipped `state_of_play`, item-count badge + arrow, and `data-testid="theme-tile"`.
  Routed `Link` to `/industry/:key` (not in-component state). Grid container keeps
  `data-testid="card-grid"`.
- **`/industry/:key`** — `ThemePage.tsx`: back link, accent bar, title, item-count/updated
  meta (from `items`), **State of Play** (`synthesis`), green **JFrog Relevance** callout
  (`--brand-jfrog-wash` / `--brand-jfrog`) headed **"What this means for JFrog"**, and a
  **Source Items** list (`↳` + `body` relevance line, evidence source link + date). Area
  chips render only when area data is present in the payload (currently omitted).
