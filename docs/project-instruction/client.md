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
  (used by tests). `isFixtureMode()` is exported so pages seed React Query
  `initialData` from fixtures **only in fixture mode**. Errors shaped
  `{ error: { message } }` reject with that message.
- Docker: `docker-compose.yml` `client` service runs `npm run dev` with
  `VITE_API_MODE=live`, `depends_on: [api]`, exposed on `5173`.

## Forced light theme
- `client/index.html` sets `<html data-theme="light">`, which pins the app to
  the light theme. `tokens.css` only applies its dark palette under
  `:root:not([data-theme="light"])` + `@media (prefers-color-scheme: dark)`, so
  the explicit attribute disables OS-driven dark mode. This keeps the UI
  identical on every machine regardless of the viewer's system theme (a dark-mode
  machine previously rendered the whole app dark, which read as a different UI).

## First-run onboarding (empty live database)
- In **live** mode the four consumer rooms pass `initialData: undefined` (no
  fixture seed), so a fresh, empty database renders an **instructive empty
  state**. It is shown **immediately whenever there is no data** — there is no
  `Loading…` placeholder and it never hangs. If a reachable API later returns
  real data the page swaps to the dashboard; if the API is unreachable the
  onboarding simply stays. In `fixture` mode the fixtures still seed
  `initialData`, so tests and offline dev are unchanged.
- `components/EmptyState.tsx` is the shared, token-styled placeholder (eyebrow,
  serif title, body, action). `components/RunNowButton.tsx` triggers the global
  batch run via `runStore.startAll()` (`POST /runs/all`) and surfaces a plain
  error if the API is unreachable; per-surface progress is shown by the existing
  `RunStatusCard`.
- Emptiness is content-aware, because some surfaces are config-scaffolded:
  - **Today** (`today-empty`) — empty when `cards` and `industry` are both empty.
    Full welcome + numbered 3-step guide + a note that Run now needs
    `OPENAI_API_KEY` in `.env`.
  - **Signals** (`signals-empty`) — empty when `items` is empty.
  - **Industry** (`industry-empty`) — themes come from config (always present),
    so empty means the **sum of theme `count`s is 0**.
  - **Competitors** (`comparison-empty`) — the matrix is scaffolded from config,
    so empty means **no cell has a real `stance` or any `evidence`**.
- Run-now failures surface the backend's readable error in a prominent
  `RunStatusCard` banner (`data-testid="run-card-alert"`). A missing/invalid
  OpenAI key is detected in `backend/app/controllers/runs.py::_readable_error`
  and returned as an actionable message ("Add OPENAI_API_KEY to your .env …
  rebuild: docker compose up --build"), so a keyless demo reads clearly rather
  than looking broken.

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
  from `NAVIGATION`. Their engine (live snapshot `ClaimVersion` / timeline) stays in
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
- **Today (`/`, daily group):** `GET /today` returns `{ headline, cards, industry }`
  — a Fraunces italic **verdict block** (amber left-rule,
  `data-testid="today-headline"`) with a tier tally strip and eyebrow meta from
  `run-status`, then two horizontal **`RailSection` rails** (not a card grid):
  a **Competitors · Recent Movements** rail (`data-testid="rail-competitors"`,
  `roomPath="/comparison"`) and an **Industry · Recent News** rail
  (`data-testid="rail-industry"`, `roomPath="/industry"`). Each rail groups its
  cards, shows one group heading + plain explainer at a time, and cross-fades /
  slides the heading as you scroll between groups (`config/railCopy.tsx`).
  - **Card destination vs. room:** a rail previews one room but its cards may open
    another via the optional `cardPath` prop. Competitor cards set
    `cardPath="/signals"` — **clicking a signal opens the Signals room, not the
    Competitors matrix** — while "See all" and the trailing card still lead to
    `roomPath`. Industry cards default to `roomPath` (`/industry`).
  - **Competitor grouping (`groupSignals`):** by `signal_type`, Hiring first.
    The backend (`/today`) already hands the client a *diversified* slice — one
    card per (competitor, kind) so a rival's near-duplicate posts collapse, spread
    across kinds — so the rail shows several tabs (Hiring, Pricing, Product,
    Security, …) rather than one kind on repeat.
  - **Industry grouping (`groupIndustry`):** by **theme bucket** (`theme_key` /
    `theme_label` from the API, e.g. *Supply chain*, *AI security*, *Pipeline*,
    *Regulation*) — the same lens the Industry page uses — **not** by signal type.
    `INDUSTRY_THEME_META` (in `railCopy.tsx`) supplies each theme's short tab
    label, accent, and explainer; it falls back to signal-type grouping only for
    items that predate theme tagging.
  Score is never exposed. Fixture: `client/src/fixtures/today.json`. Query keys:
  `["today"]`, `["run-status"]` (eyebrow date + sources tally).
- **Competitors (`/comparison`):** a **competitor × capability-dimension matrix**
  (`ComparisonGrid`) from `GET /comparison/matrix`, transposed client-side over
  the API's **dimension** rows (five buyer-facing columns). Each cell shows
  `stance` as strength (Strong/Moderate/Weak/None — `none` is empty/neutral)
  plus summary; row click opens `CompetitorDetail` with per-dimension cards and
  sourced evidence links — never a numeric grade and never a `was → now` diff
  (see [comparison.md](./comparison.md)). The page opts out of the shared
  `--content-max` (900px) via `.app-shell__main > .comparison-page` so the
  six-column grid can use up to **1480px** of the main pane. **Run this page**
  triggers `api.runSurface("comparison")` and refreshes `["comparison-matrix"]`.
  The legacy claim-by-claim `/comparison` list still exists for the benched
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
  numbered suggested questions — grounded prompts aligned to the collected signal
  categories (competitor cards, industry themes, hiring signals, changelog entries), so
  they resolve against data we actually hold. Each submit calls `POST /chat/stream`
  (`api.postChatStream`), rendering answer tokens live and then appending a user bubble +
  grounded answer (green citation badges via `<CitationCard>` / `<Cited>` /
  `<SourceLink>`, whose links point to the finding's origin URL) or a `<RefusalNotice>`.
  Fixture mode matches questions to canned exchanges in `selectAskFixture`.
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
