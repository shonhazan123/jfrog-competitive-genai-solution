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

## Active competitor set

`config/competitors.yaml` lists the slugs on the Signals/Comparison grid (currently
github, sonatype, snyk, aqua, checkmarx). Other competitor entities (gitlab, harbor,
azure_artifacts) remain in `config/entities.yaml` but are off the grid.

`app.services.research.competitors.load_competitors()` joins the allowlist with
entity names and aliases from `entities.yaml`.

## Instructions

`current_instructions()` loads `config/instructions.yaml` (or the in-process override
from `PUT /config/instructions`). The API persists and returns analyst free-text
instructions; there is no live path that injects them into interpret LLM prompts in
Phase 0.

## Tiers (verdict thresholds)

Tier labels and thresholds are config, not code:

- `config/materiality.yaml` → `tiers: { act_on_it, worth_knowing }` numeric cutoffs.
- `config/labels.yaml` → `tiers: { act_on_it, worth_knowing, background }` display words.
- `app.services.scoring.materiality.tier_for(total, config)` maps an internal score
  to a tier; `primary_stakeholder(scores)` picks the lead persona; `tier_priority(tier)`
  (`act_on_it`=3, `worth_knowing`=2, `background`=1) ranks cards and email/digest items
  now that the numeric `score` is no longer serialised.
