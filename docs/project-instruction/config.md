# Config — intention-based settings

Settings moved from numeric weight tuning to **stating intent**: who to watch and
what the analyst cares about. The old `PUT /config/materiality` weight editor is
gone from the UI (the endpoint still exists for internal re-scoring); Settings now
edits competitors and free-text instructions.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET / PUT | `/config/competitors` | Which competitors to track — applies a **watchlist** override (`config/watchlist.yaml` via `apply_watchlist_override`) |
| GET / PUT | `/config/instructions` | Free-text analyst instructions (`config/instructions.yaml`) |

Handled in `app.controllers.config` + `app.routers.config`. Overrides are held in
process (`_instructions_override`, watchlist override) and bump a config version;
`clear_config_extensions()` resets them (used by tests).

## Instructions injection

`current_instructions()` loads `config/instructions.yaml`. `agent_service` appends
the text into the **Analyst instructions** section of both `agent/prompts/extract.md`
and `agent/prompts/contextualize.md`, so the analyst's intent steers extraction and
the `why_it_matters` one-liner without any code change. Empty instructions leave the
prompts unchanged.

## Tiers (verdict thresholds)

Tier labels and thresholds are config, not code:

- `config/materiality.yaml` → `tiers: { act_on_it, worth_knowing }` numeric cutoffs.
- `config/labels.yaml` → `tiers: { act_on_it, worth_knowing, background }` display words.
- `app.services.scoring.materiality.tier_for(total, config)` maps an internal score
  to a tier; `primary_stakeholder(scores)` picks the lead persona; `tier_priority(tier)`
  (`act_on_it`=3, `worth_knowing`=2, `background`=1) ranks cards and email/digest items
  now that the numeric `score` is no longer serialised.
