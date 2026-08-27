# Client — operational flow

The React client (`client/`) is **verdict-first**: every consumer screen hands the
reader a plain judgement (a tier word + a one-line reason) backed by a clickable
source, with **no numbers and no historical diffing** on any consumer surface
(Today, Competitors, Signals, Industry, Divisions, Email). It is built and tested
against `client/src/fixtures/*.json` and switched to the live API by one flag.

## Mode switch
- `VITE_API_MODE` ∈ `fixture` (default) | `live`; `VITE_API_BASE` (default
  `http://localhost:8000`) is the live base URL. `client/src/api/client.ts`
  resolves every read from the imported fixture in `fixture` mode and calls
  `fetch(base + path, init ?? {})` in `live` mode. `setMode()` flips it at runtime
  (used by tests). Errors shaped `{ error: { message } }` reject with that message.
- Docker: `docker-compose.yml` `client` service runs `npm run dev` with
  `VITE_API_MODE=live`, `depends_on: [api]`, exposed on `5173`.

## Structure that encodes decisions
- **IA is data:** `client/src/config/navigation.ts` (`NAVIGATION`, grouped
  `daily`/`reference`/`tools`). Regrouping never touches JSX. The sidebar primary
  group mirrors Figma's five daily rooms: **Today** `/`, **Competitors**
  `/comparison`, **Signals** `/signals`, **Industry** `/industry`, **Ask** `/ask`.
  Secondary groups hold **Divisions** `/divisions` (reference) and **Settings**
  `/settings`, **Email Digest** `/digest` (tools). Mobile bottom bar shows the
  five `primary` daily items only.
- **Change-detection pages are benched, not deleted:** `Trajectory`
  (`/trajectory`), `Competitors → Us` (`/about-us`), and `ClaimTimeline` remain
  in the repo and reachable by direct URL for the roadmap story, but are removed
  from `NAVIGATION`. Their engine (backfill / `ClaimVersion` / timeline) stays in
  the backend, off every primary surface (single-snapshot rule).
- **Signals room (`/signals`, daily):** reads `GET /signals`, filtered client-side
  by `signal_type` via a `FilterChips` bar (All + present types with counts),
  grouped into nine-type sections (`product_capability` … `talent_org`) with
  mono headers and per-type `signalHue` accents, and rendered as collapsed
  `SignalAccordionRow`s that expand in place to an **Intent read** body
  (`so_what`, `why_it_matters` tier reason, audience tag, evidence quote +
  clickable source). Framed as *intent* ("what this reveals"), never "what
  changed". No persona tabs (that is Divisions). `SignalCard` (actions + trace)
  is not used on this surface. **Run this page** calls `api.runSurface("signals")`
  and invalidates `["signals"]` on completion.
- **Divisions (`/divisions`, reference):** the same intel read through a persona
  lens. Three `role="tab"` buttons (Sales / Product / Executive) switch the
  source list; Sales/Product mirror the **Signals design** — a `FilterChips` type
  (tag) bar (`data-testid="division-type-filter"`) over signals **grouped into
  clear per-company sections** (`data-testid="division-company-{slug}"`, mono
  company header + count + rule) rendered as expand-in-place `SignalAccordionRow`s.
  Executive stays a sparse `TrendCard` + stability summary. No `card-grid` here
  anymore (that pattern now lives on Industry).
- **Card grids:** the responsive `repeat(auto-fill, minmax(…, 1fr))` grid inside
  `data-testid="card-grid"` (with `data-columns` `"1"` below 1000px, else `"auto"`)
  is used by **Industry** (a grid of **theme tiles**, see
  [industry.md](./industry.md)) and **Today** (the `IntelCard` grid).
- **All styling is tokens:** `client/src/styles/tokens.css` is the entire visual
  language (colour, type scale, spacing, radius, elevation, dark override). No
  component hardcodes a hex — a test scans every `.tsx` for `#rrggbb`. Fonts:
  Outfit (`--font-sans`), Fraunces (`--font-serif` / `.font-display`), DM Mono
  (`--font-mono` / `.mono-label`). Tier colours: amber act-on-it (`--tier-act`),
  blue worth-knowing (`--tier-worth`), slate background (`--tier-bg`) with
  matching `--*-wash` surfaces; JFrog brand green (`--brand-jfrog`). Signal hue
  tokens (`--sig-*`) drive type chips. `/styleguide` (`StyleGuide.tsx`) is the
  living reference for all of the above plus primitive states.
- **SignalCard rule (non-negotiable):** entity, type, the **tier verdict**
  (`<TierBadge tier tier_label />`, coloured pill, never a number), the headline,
  the prominent `why_it_matters` one-liner, the full `so_what`, and the verbatim
  first `evidence` quote whose **source is always a clickable `<a href=source_url>`
  + date** are ALWAYS visible. Only `HOW THIS WAS PRODUCED` (provenance trace)
  collapses. There is no score and no "Why this score" breakdown, and no
  `was → now` change block (all removed in the verdict-first redesign).
- **Today (`/`, daily group):** `GET /today` returns `{ headline, cards }` — a
  Fraunces italic **verdict block** (amber left-rule, `data-testid="today-headline"`)
  with a tier tally strip and eyebrow meta from `run-status`, then at most five
  read-only `IntelCard`s in a responsive grid (`repeat(auto-fill,
  minmax(380px, 1fr))`, `data-testid="card-grid"`). Cards are ranked by tier then
  internal materiality (score never exposed). The heavy `SignalCard` (actions +
  trace) is reserved for Signals/Divisions; Today uses the lean `IntelCard` only.
  The KIT grid is retired. Fixture: `client/src/fixtures/today.json`. Query keys:
  `["today"]`, `["run-status"]` (eyebrow date + sources tally).
- **Competitors (`/comparison`):** a **competitor × capability-dimension matrix**
  (`ComparisonGrid`) from `GET /comparison/matrix`, transposed client-side over
  the API's **dimension** rows (five buyer-facing columns). Each cell shows
  `stance` as strength (Strong/Moderate/Weak/None — `none` is empty/neutral)
  plus summary; row click opens `CompetitorDetail` with per-dimension cards and
  sourced evidence links — never a numeric grade and never a `was → now` diff
  (see [comparison.md](./comparison.md)). **Run this page** triggers
  `api.runSurface("comparison")` and refreshes `["comparison-matrix"]`. The
  legacy claim-by-claim `/comparison` list still exists for the benched
  `about-us`/`trajectory` pages but is off the primary surface.
- Responsive: AppShell switches sidebar (≥900px) ↔ bottom bar of five `primary`
  daily items (<900px) in JS by `window.innerWidth`.
- **Human vocabulary layer:** `client/src/config/labels.ts` mirrors
  `config/labels.yaml` — `signalTypeLabel`, `priorityLabel`, `stateLabel`,
  `personaLabel`, `originLabel`, and `signalHue` so consumer screens never
  hardcode machine values. Pages import from here; Settings is the carve-out.
- **Settings is intention-based:** the numeric `WeightEditor` is gone. Settings
  now hosts `CompetitorEditor` (which competitors to track, `GET/PUT
  /config/competitors`) and `InstructionsEditor` (free-text analyst instructions
  injected into extract/contextualize prompts, `GET/PUT /config/instructions`).
- **Mandatory citations (two demo promises):** Every assertion must pass through
  `<Cited citation={…}>` (renders nothing without a citation) and cite its
  origin via `<SourceLink citation={…}>` (clickable link, or "Authored by the
  CI team" for authored positions). `TierBadge` shows the tier word
  (`tier_label`), never a raw score. `citation.test.tsx` enforces both promises
  structurally.

## Contract drift found at live wiring (fix in the backend / Plan 3, not the client)
- **Score fields removed from consumer payloads.** `/today`, `/signals`,
  `/digests/{persona}`, and `/comparison/matrix` expose `tier` / `tier_label` /
  `primary_stakeholder` / `why_it_matters` and never `score` or `score_breakdown`.
  The numeric arithmetic still runs internally (persona scores drive the tier via
  `tier_for`, and the active persona's score picks the row's tier) but is never
  serialised to a consumer screen.
- **`POST /ask`** returns a single `AskResponse`; the client fixture
  `ask_transcript.json` is a `{ exchanges: [...] }` demo transcript with no matching
  single endpoint. The Ask screen (`/ask`) is an interactive chat: empty state shows
  numbered suggested questions (static prompts aligned to fixture exchanges); each submit
  calls `POST /ask` and appends a user bubble + grounded answer (green citation badges via
  `<CitationCard>` / `<Cited>` / `<SourceLink>`) or a `<RefusalNotice>`. Fixture mode
  matches questions to canned exchanges in `selectAskFixture`.
- **No fixture / no client method** for `GET /digests/{persona}` (sales/product);
  digest header counts are not wired for sales/product.
- **Non-blocking run indicator:** `StatusStrip` in the AppShell header (persists
  across route changes) exposes **Run now** → `POST /runs` → poll `GET /runs/{id}`
  every 1.5s. `RunProgress` shows the human `stage_label` and a `current/total`
  counter — never a modal or full-page spinner. On `done`, the client invalidates
  the daily query keys `["today"]`, `["signals"]`, `["run-status"]`, `["industry"]`,
  `["comparison"]` (the retired `["kits"]` key is no longer used), then surfaces
  `N new items`. On `failed`, it shows the plain-language `message`.
  Fixture mode returns an immediate `done` progress so the UI does not hang.
  **`api.runSurface(kind)`** (`industry` | `signals` | `comparison`) POSTs the
  surface kind, polls to completion (reusing `RUN_POLL_INTERVAL_MS`), and is
  wired to **Run this page** on Industry, Signals, and Comparison — each page
  invalidates its own query keys on success.
- `GET /email/preview?persona=…` ignores the `persona` query param and returns all
  three personas keyed (`sales`/`product`/`exec`) — the client fixture is keyed the
  same way, so the client works; the server-side param is a no-op.
- Coverage matrix has 8 signal columns (omits `corporate_financial`); the table
  renders 9 header cells (entity label + 8), per contract §7.7 / gap G12.
- `sources.json` states the ToS exclusion as "ToS prohibits automated collection
  (G2)" (abbreviation, not "Terms of Service").
