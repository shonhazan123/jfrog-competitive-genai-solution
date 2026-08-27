# Plan — Fix collection starvation & route every item to the right surface

**Date:** 2026-08-27
**Status:** Proposed (backend implementation plan)
**Depends on / supersedes framing in:** the source-coverage analysis from this session.

## Goal

Stop the pipeline from starving on one competitor, feed **every** competitor entity, and make
sure each collected item becomes a **correctly-classified, correctly-sourced signal** that lands
on the right surface — so the currently-empty pages (Competitors matrix, Industry → Funding,
Industry → AI/MLOps) fill, and JFrog self-cards disappear.

## Confirmed decisions (from the user)

1. **Competitor scope: registry rivals only** — the five `kind: competitor` entities already in
   [entities.yaml](config/entities.yaml): **Sonatype, GitHub Packages, GitLab, Harbor, Azure
   Artifacts**. Security/SCA vendors (Snyk/Aqua/Checkmarx) are **out of scope** — they were the
   POC's mistake, not the compass.
2. **JFrog data = authored baseline only** — delete the `jfrog_homepage` scrape. JFrog's own
   position lives solely in [jfrog_positions.yaml](config/jfrog_positions.yaml) (`origin:
   authored`), used as the comparison baseline, never emitted as a signal.

## Root causes (verified in code + a live run)

1. **The source set feeds ~1.5 competitors.** Of 11 sources, 5 are Sonatype, 1 Harbor, 1 JFrog-self,
   4 generic industry. **GitHub Packages, GitLab, and Azure Artifacts have zero source rows** →
   their matrix columns are permanently `no_claim`.
2. **The matrix and the signals are fed by two paths that never talk.** [comparison_matrix.py]
   (backend/app/services/comparison_matrix.py) `_claim_for_component` fills a cell only when a
   **dimensioned `Claim`** exists (`asserting_entity = competitor`, `Claim.dimension ∈ component
   dimensions`). Today those come **only** from the comparison-page diff path
   ([backfill.py](backend/app/services/backfill.py) `_apply`), which runs for Sonatype's compare
   page alone. The LLM interpret path produces `Signal`s that are **never written as matrix
   claims** — so rich collection still leaves the matrix empty.
3. **Snapshot captures get re-injected into the LLM queue.** [jobs.py](backend/worker/jobs.py)
   `run_interpret` drains every un-interpreted `RawCapture` regardless of mode. Wayback backfill
   creates one capture per archived version of the compare page, so the model re-reads near-
   identical pages (the 12/6/14 duplicate-claim runs). Positioning pages are thus extracted twice.
4. **The JFrog scrape emits self-cards** — nonsense competitive cards about JFrog itself.
5. **Industry Funding & AI/MLOps are empty**; "Other" catches 4. [industry_themes.py]
   (backend/app/services/industry_themes.py) `assign_theme` needs `signal_type ∈ theme.signal_types`
   **and** a keyword hit, over signals whose `entity = industry`. No funding source, no model-
   registry source, and off-taxonomy items fall to "Other".

---

## Workstreams

### A — Remove JFrog self-probing (objective 1)
- Delete the `jfrog_homepage` row from [sources.yaml](config/sources.yaml).
- **Self-guard (belt-and-braces):** in `interpret_capture` (agent_service) refuse to emit any
  `Signal` whose `subject_entity` or `asserting_entity` is `kind == "self"`. A competitor page
  that quotes JFrog must never spawn a JFrog card.
- No matrix regression: `build_comparison_matrix` reads JFrog's column from
  `jfrog_positions.yaml` via `_jfrog_position_for_dimension` (verified) — independent of the scrape.
- **Test:** assert no active `Signal` resolves to an entity of `kind = self`.

### B — Feed every competitor (breadth) — sources verified live this session
New rows for [sources.yaml](config/sources.yaml). ✅ = fetched 200 + valid feed today.

| Competitor | Source | URL | kind/mode | grade | covers |
|---|---|---|---|---|---|
| Sonatype | *(existing)* nexus releases, compare page, Lever jobs, OSV | — | — | A | product/positioning/talent |
| Harbor | harbor releases ✅ *(existing)* | `github.com/goharbor/harbor/releases.atom` | atom/feed | A | product_capability |
| **GitHub Packages** | github changelog ✅ | `github.blog/changelog/feed/` | rss/feed | A | product_capability, positioning |
| **GitHub Packages** | github blog ✅ | `github.blog/feed/` | rss/feed | B | positioning_messaging |
| **GitLab** | gitlab blog/releases ✅ | `about.gitlab.com/atom.xml` | atom/feed | A | product_capability, pricing, positioning |
| **Azure Artifacts** | azure news ⚠️ | Google-News RSS query `"Azure Artifacts" OR "Azure DevOps Artifacts"` | rss/feed | C | product_capability |

Notes:
- The GitLab repo `releases.atom` **404s** — dropped; the blog atom carries the monthly release
  posts and works (20 entries).
- **Azure Artifacts has no clean official feed** (the updates feed isn't valid XML). Until one is
  found, it rides the news lane at grade C — its column may stay thin. Follow-up: verify
  `learn.microsoft.com` Azure DevOps release-notes feed.
- Filter GitHub's changelog to Packages/registry items (keyword gate on the source) so GitHub's
  broad changelog doesn't flood the queue.

### C — Structural starvation fixes
- **Exclude snapshot captures from the LLM queue.** In `run_interpret`, join `RawCapture → Source`
  and filter `Source.mode != "snapshot"`. Snapshot pages are already handled deterministically by
  the diff path — this stops the re-chewing (root cause 3) with one clause.
- **Per-source capture cap per run** (e.g. ≤ 3 from one source) as a flood guard.
- **Freshness on manual runs:** widen API/news adapters to a rolling ~30-day window on `manual`
  (not just "since last check"), so a demo run has substance instead of ~2 captures.
- **Positioning going forward:** keep the compare-page diff for Sonatype only; every other
  competitor's positioning is carried by the feeds in B and turned into matrix claims by D.

### D — Bridge signals → dimensioned matrix claims (objectives 2 + 3, matrix) — **the key fix**
The `capability_tags` enum in [signal_types.yaml](config/signal_types.yaml) is **identical** to the
`dimensions` in [jfrog_components.yaml](config/jfrog_components.yaml) (`malware_detection`, `sbom`,
`model_registry`, `package_format_support`, `deployment_model`, `vulnerability_scanning`,
`policy_engine`, `runtime_security`, `build_provenance`). Interpret already produces
`capability_tags` on each signal (a recent run logged `capability_tags=10/5/13`). So:

- When interpret finishes a **competitor** signal carrying `capability_tags`, **upsert a `Claim`**
  per tag: `subject = jfrog`, `asserting = competitor entity`, `dimension = <tag>`,
  `claim_text = so_what_product or headline`, `reliability_grade = source grade`,
  `claim_type = "positioning"`, plus an `Evidence` row from the capture's verified quote.
- `_claim_for_component` then fills that competitor's cell — **for all five rivals, from the LLM
  path**, not just the Sonatype diff path. No new mapping table needed; the tag *is* the dimension.
- Edge: `pricing_model` is a `capability_tag` but not in any component's dimensions — either add a
  pricing component/dimension or accept pricing routes to Signals only. (Minor; note it.)
- Guard: write a claim only from **graded, quote-backed** evidence — never synthesize a cell. This
  keeps the matrix honest (no fabricated confidence).

### E — Fill Industry themes & shrink "Other" (objectives 2 + 3, industry)
Add `entity: industry` sources so each theme in [themes.yaml](config/themes.yaml) has fuel:

| Theme (empty/thin) | New source | URL | grade | routes via |
|---|---|---|---|---|
| **Funding & acquisitions** | Google-News funding query ✅ | `news.google.com/rss/search?q=(Sonatype OR GitLab OR Harbor OR "GitHub Packages") (acquisition OR funding OR raises OR series)` | C | corporate_financial + keyword |
| **AI/MLOps & model registries** | HuggingFace blog ✅ | `huggingface.co/blog/feed.xml` | B | product_capability + model/registry |
| **AI/MLOps** | Google-News model-registry ✅ | `news.google.com/rss/search?q="model registry" OR MLOps artifact` | C | product_capability + keyword |
| **Supply-chain & CVEs** | CISA advisories ✅ *(+ existing OSV)* | `cisa.gov/cybersecurity-advisories/all.xml` | A | security_trust + keyword |
| **Regulation & compliance** | CISA / (later ENISA, EUR-Lex) | as above | A | market_regulatory |

Routing correctness (kills "Other"):
- Give each industry source a `covers:` signal-type hint and make `extract` honor it, so items land
  in the theme's `signal_types`.
- Extend `assign_theme` to **fall back to the source `covers` hint** when the keyword test fails
  (or broaden `themes.yaml` keywords). Config-level, low risk.
- **Routing nuance to make explicit:** a competitor's *own* AI move (e.g. GitLab ships a model
  registry) is `entity = gitlab` → it fills **Signals + the matrix `model_registry` cell**, not the
  industry-wide AI/MLOps theme (which is `entity = industry`). Both surfaces get fed, by different
  sources. Set expectations accordingly.

### F — Sourcing correctness (objective 2)
- Grade every new row: **A** official vendor/GitHub/gov feeds; **B** docs/blogs; **C** news/aggregator/HN.
- Citations already work for feed/api items (source_url + captured_at). Google-News items cite the
  underlying publisher; keep grade C and label aggregator provenance.
- **Honest caveat:** Google News RSS is widely used but not an official API. Acceptable for internal
  CI at grade C; swap to GDELT or official regulator feeds for a production posture.

---

## Verification — what "filled" must look like
- **Competitors matrix:** after a manual run, each of the 5 rivals shows ≥ 1 non-`no_claim` cell
  backed by real evidence (workstream D). No column is entirely empty except possibly Azure.
- **Industry:** Funding ≥ 1, AI/MLOps ≥ 1, "Other" strictly smaller.
- **No self-cards:** zero active signals resolve to `kind = self`.
- **No re-chewing:** interpret no longer drains snapshot captures; one page → one pass → many claims.
- **Tests:** update `test_comparison_matrix` (bridge), `test_industry_themes` (new themes fill),
  `test_jobs`/`test_interpret_graph` (snapshot exclusion); add a self-guard test.

## Staged execution
1. **A** — remove JFrog scrape + self-guard + test. *(fastest, stops the dumb cards)*
2. **C** — snapshot-out-of-queue + per-source cap. *(immediately stops re-chewing)*
3. **B** — add the verified competitor source rows. *(breadth)*
4. **D** — signal→claim bridge. *(fills the matrix; the biggest code change)*
5. **E** — industry sources + routing fallback. *(fills Funding/AI-MLOps, shrinks Other)*
6. **F** — grades/citations pass, then a full manual run to confirm the verification checklist.

## Risks & guardrails
- **Aggregator provenance/ToS** (Google News): grade C, swap in prod.
- **Azure Artifacts** has no clean feed — news-lane only until one is found; its column may stay thin.
  Don't paper over it with a fabricated cell.
- **Matrix over-population:** the bridge must write cells only from graded, quote-backed evidence;
  weak/ungraded tags stay in Signals. The authored JFrog position remains the anchor.
- **Classification drift:** monitor "Other" after E; the `covers` fallback + keywords mitigate but
  don't eliminate misrouting.
- **No fabrication, ever:** every new claim/signal traces to a real verified quote. Matching the
  mock's *coverage* must never mean matching its *invention*.
