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
  `daily`/`reference`/`tools`). Regrouping never touches JSX. The verdict-first
  sidebar is eight items: **Today** `/`, **Competitors** `/comparison`,
  **Signals** `/signals`, **Industry** `/industry` (daily); **Divisions**
  `/divisions` (reference); **Ask** `/ask`, **Settings** `/settings`,
  **Email Digest** `/digest` (tools).
- **Change-detection pages are benched, not deleted:** `Trajectory`
  (`/trajectory`), `Competitors → Us` (`/about-us`), and `ClaimTimeline` remain
  in the repo and reachable by direct URL for the roadmap story, but are removed
  from `NAVIGATION`. Their engine (backfill / `ClaimVersion` / timeline) stays in
  the backend, off every primary surface (single-snapshot rule).
- **Signals room (`/signals`, daily):** reads `GET /signals` grouped client-side
  by `signal_type` and rendered with `SignalCard`, framed as *intent* ("what this
  reveals"), never "what changed". No persona tabs (that is Divisions).
- **Card grids (Divisions):** signal cards use
  `repeat(auto-fill, minmax(420px, 1fr))` inside `data-testid="card-grid"`.
  `data-columns` is `"1"` when viewport width &lt; 1000px, otherwise `"auto"`.
  Industry is now a grid of **theme tiles** (see [industry.md](./industry.md)),
  not a signal-card grid.
- **All styling is tokens:** `client/src/styles/tokens.css` is the entire visual
  language (colour, type scale, spacing, radius, elevation, dark override). No
  component hardcodes a hex — a test scans every `.tsx` for `#rrggbb`.
- **SignalCard rule (non-negotiable):** entity, type, the **tier verdict**
  (`<TierBadge tier tier_label />`, coloured pill, never a number), the headline,
  the prominent `why_it_matters` one-liner, the full `so_what`, and the verbatim
  first `evidence` quote whose **source is always a clickable `<a href=source_url>`
  + date** are ALWAYS visible. Only `HOW THIS WAS PRODUCED` (provenance trace)
  collapses. There is no score and no "Why this score" breakdown, and no
  `was → now` change block (all removed in the verdict-first redesign).
- **Today (`/`, daily group):** `GET /today` returns `{ headline, cards }` — a
  single composed verdict sentence plus at most five full-width `SignalCard`s
  ranked by tier then internal materiality (score never exposed). The KIT grid is
  retired. Fixture: `client/src/fixtures/today.json`. Query key: `["today"]`.
- **Competitors (`/comparison`):** a **JFrog-component × competitor matrix**
  (`ComparisonGrid`) from `GET /comparison/matrix`, built over
  `config/jfrog_components.yaml`. Each cell is a single-snapshot **stance**
  (`comparable` when the competitor has a public claim on the component, else
  `no_claim`) shown against JFrog's authored `jfrog_position`, with a clickable
  source — never a numeric grade and never a `was → now` diff (see
  [comparison.md](./comparison.md)). The legacy claim-by-claim `/comparison` list
  still exists for the benched `about-us`/`trajectory` pages but is off the
  primary surface.
- Responsive: AppShell switches sidebar (≥900px) ↔ bottom bar of `primary` items
  (<900px) in JS by `window.innerWidth`.
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
  single endpoint. The Ask screen renders the canned transcript in fixture mode;
  live mode answers one question per POST.
- **No fixture / no client method** for `GET /digests/{persona}` (sales/product);
  digest header counts are not wired for sales/product.
- **Non-blocking run indicator:** `StatusStrip` in the AppShell header (persists
  across route changes) exposes **Run now** → `POST /runs` → poll `GET /runs/{id}`
  every 1.5s. `RunProgress` shows the human `stage_label` and a `current/total`
  counter — never a modal or full-page spinner. On `done`, the client invalidates
  the daily query keys `["today"]`, `["signals"]`, `["run-status"]` (the retired
  `["kits"]` key is no longer used), then surfaces `N new items`. On `failed`, it
  shows the plain-language `message`.
  Fixture mode returns an immediate `done` progress so the UI does not hang.
- `GET /email/preview?persona=…` ignores the `persona` query param and returns all
  three personas keyed (`sales`/`product`/`exec`) — the client fixture is keyed the
  same way, so the client works; the server-side param is a no-op.
- Coverage matrix has 8 signal columns (omits `corporate_financial`); the table
  renders 9 header cells (entity label + 8), per contract §7.7 / gap G12.
- `sources.json` states the ToS exclusion as "ToS prohibits automated collection
  (G2)" (abbreviation, not "Terms of Service").
