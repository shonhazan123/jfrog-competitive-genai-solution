# Client — operational flow

The React client (`client/`) renders all nine screens. It is built and tested
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
  `daily`/`reference`/`tools`). Regrouping never touches JSX. The router registers
  all nine routes + a dev `/styleguide`; page tasks only fill their own page file.
  **Trajectory** (`/trajectory`, reference group, immediately after Industry) is
  the dedicated archive tab — how a competitor's comparison argument evolved
  over five years, with dated Wayback captures and `SourceLink` per version.
  **Competitors → Us** (`/about-us`) keeps current claims and links to
  Trajectory via "View full history"; the multi-year timeline no longer renders
  there.
- **Card grids (Divisions, Industry):** signal cards use
  `repeat(auto-fill, minmax(420px, 1fr))` inside `data-testid="card-grid"`.
  `data-columns` is `"1"` when viewport width &lt; 1000px, otherwise `"auto"`.
- **All styling is tokens:** `client/src/styles/tokens.css` is the entire visual
  language (colour, type scale, spacing, radius, elevation, dark override). No
  component hardcodes a hex — a test scans every `.tsx` for `#rrggbb`.
- **SignalCard rule (non-negotiable):** entity, type, score, headline, the full
  `so_what`, and the verbatim first `evidence` quote + source line are ALWAYS
  visible; only `WHY THIS SCORE` and `HOW THIS WAS PRODUCED` collapse.
- **Comparison:** JFrog cells are `authored` and carry no grade; competitor cells
  carry a grade + evidence; an absent claim reads "No public claim" with no grade.
  Diffs render as `was → now`, never a code diff.
- Responsive: AppShell switches sidebar (≥900px) ↔ bottom bar of `primary` items
  (<900px) in JS by `window.innerWidth`.
- **Human vocabulary layer:** `client/src/config/labels.ts` mirrors
  `config/labels.yaml` — `signalTypeLabel`, `priorityLabel`, `stateLabel`,
  `personaLabel`, `originLabel`, and `signalHue` so consumer screens never
  hardcode machine values. Pages import from here; Settings is the carve-out.
- **Mandatory citations (two demo promises):** Every assertion must pass through
  `<Cited citation={…}>` (renders nothing without a citation) and cite its
  origin via `<SourceLink citation={…}>` (clickable link, or "Authored by the
  CI team" for authored positions). `PriorityBadge` shows the band word, never
  the raw score. `citation.test.tsx` enforces both promises structurally.

## Contract drift found at live wiring (fix in the backend / Plan 3, not the client)
- **`score_breakdown` is `null`** on every `/signals` and `/digests/{persona}` list
  item (confirmed live). The score arithmetic exists only on `GET /signals/{id}`
  (contract §1.5). SignalCard shows "Score breakdown not available" for list items.
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
  `["kits"]`, `["signals"]`, `["run-status"]`, and other daily query keys, then
  surfaces `N new items`. On `failed`, it shows the plain-language `message`.
  Fixture mode returns an immediate `done` progress so the UI does not hang.
- `GET /email/preview?persona=…` ignores the `persona` query param and returns all
  three personas keyed (`sales`/`product`/`exec`) — the client fixture is keyed the
  same way, so the client works; the server-side param is a no-op.
- Coverage matrix has 8 signal columns (omits `corporate_financial`); the table
  renders 9 header cells (entity label + 8), per contract §7.7 / gap G12.
- `sources.json` states the ToS exclusion as "ToS prohibits automated collection
  (G2)" (abbreviation, not "Terms of Service").
