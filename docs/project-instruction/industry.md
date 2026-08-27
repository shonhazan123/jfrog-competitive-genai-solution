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
