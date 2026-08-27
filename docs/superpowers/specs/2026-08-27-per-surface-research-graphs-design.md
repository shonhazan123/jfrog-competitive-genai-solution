# Per-Surface Research Graphs — Design Spec

**Date:** 2026-08-27
**Status:** Design approved in brainstorming; pending spec review before implementation plan.
**Topic:** Replace the single `interpret` pipeline with three dedicated LangGraph research agents, one per surface (Industry, Signals, Comparison).

---

## 1. Problem

Today a single graph — `interpret_capture` ([agent_service.py:268](../../../backend/app/services/agent_service.py)) — runs over *every* `RawCapture` regardless of which page it feeds. All three product surfaces are downstream of it:

- **Industry radar** = `Signal`s on the `industry` entity, seeded from whatever RSS feeds emit (HackerNews, TheNewStack, HuggingFace blog). There is **no DevSecOps topicality gate**, so off-field items ("4-bit quantized model", "GraphRAG") get a `signal_type` and surface as radar. Worse, the current `ai_mlops` theme in `themes.yaml` matches on `model, ml, llm, registry` — the config **actively invites** the noise.
- **Signals page** = the same `Signal`s, faceted by type. Hiring coverage is 1-of-5 (only `sonatype_jobs` via Lever is wired); everything else is fixture/seed data.
- **Comparison grid** = `Claim` rows produced as a *side-effect* when a competitor signal happens to carry a capability tag ([agent_service.py:137](../../../backend/app/services/agent_service.py)). Cells fill only by luck of RSS phrasing, and strength is not even stored (see §6).

**Root cause:** one pipeline, passive RSS seeding, no per-surface relevance contract.

## 2. Goals / Non-goals

**Goals**
- Three dedicated research agents, one per page, each with its own strict relevance contract.
- Directed web search (+ structured sources where they exist) replaces passive RSS seeding for these three surfaces.
- Each agent guarantees every box on its page is **resolved** — filled-and-sourced *or* proven-absent — never fabricated, never looping forever.
- `Run now` (Today) fans out to all three; each page fills independently as its agent finishes. Each page also gets a `Run this page` button for iteration.

**Non-goals (this iteration)**
- Quote-verification of web results (we chose lightweight synthesis; see §3).
- Incremental "only refresh stale cells" for Comparison (deferred; rebuild all for now).
- Retiring the `interpret` path for surfaces the new agents do **not** own (OSV security advisories, the Ask corpus stay).

## 3. Locked decisions (from brainstorming)

1. **Lightweight synthesis** — the agent's own summary is shown; **but every card keeps its real `source_url`** (traceable, even if not quote-verified).
2. **LangGraph graph per surface** — retry loops and web-search fallback are expressed as conditional edges.
3. **Search vendor:** OpenAI native `web_search` tool. Search + LLM construction live in the `agent` package; `app/services` calls in and does DB writes (respects the existing "app never constructs the LLM layer" boundary).
4. **Tiered pattern per box:** structured source → LLM relevance/usable gate → web-search fallback → retry → resolve-or-absent.
5. **All gates are LLM**, Industry included. Each agent has a **strict system prompt** that checks its page's fill-contract box by box.
6. **Termination = resolved-or-absent, cap 3.** Loop until every box is filled-and-sourced OR the LLM reasons it is genuinely absent (→ `none`/empty/drop). Hard cap of 3 attempts per box; on exhaustion, remaining boxes are marked absent. No fabrication, no infinite loop.
7. **Reuse existing tables** (`Signal` / `Claim` / industry), retire the noisy RSS→interpret seeding for these 3 surfaces; keep OSV + Ask.
8. **Run model:** per-page runs + a Today fan-out; each surface has its own `run_id` and progress.
9. **Competitors:** GitHub, Sonatype, Snyk, Aqua Security, Checkmarx.
10. **Comparison columns (5):** Artifact Management, SCA/SBOM, Container Security, CI/CD Integration, Developer Experience.

## 4. Architecture

```
agent/                      (owns LLM + tools + graph construction)
  tools/web_search.py       NEW — OpenAI native web_search tool wrapper
  graphs/research/
    skeleton.py             NEW — shared state + plan/assess/fallback/loop grammar
    industry/graph.py       NEW
    signals/graph.py        NEW
    comparison/graph.py     NEW
  prompts/
    research_industry.md    NEW — strict per-agent system prompt
    research_signals.md     NEW
    research_comparison.md  NEW

app/services/research/       (owns DB writes; calls agent graphs)
  industry_agent.py          NEW — runs graph, persists Signals(+theme_key)
  signals_agent.py           NEW — runs graph, persists Signals
  comparison_agent.py        NEW — runs graph, persists Claims(+stance)
  provenance.py              NEW — synthetic Source + RawCapture stub per accepted result

worker/jobs.py               run_industry() / run_signals() / run_comparison()
app/controllers/runs.py      per-surface run kinds + Today fan-out
```

### Dependency boundary
`app/services/research/*` imports `agent.graphs.research.*` and `agent.tools.web_search` **only through the graph entry points**, exactly as `agent_service.py` imports `build_interpret_graph` today. The `agent` package never imports `app.models`.

## 5. The shared skeleton

All three graphs specialise one grammar. State (a `TypedDict`):

```python
class ResearchState(TypedDict):
    targets: list[dict]     # work units (see per-agent)
    cursor: int             # index of the target being worked
    attempts: int           # attempts spent on targets[cursor]
    drafts: list[dict]      # resolved boxes (filled OR absent), ready to persist
    max_attempts: int       # = 3, from config
    status: str
```

Nodes and edges (`assess` is the conditional edge that holds the logic):

```
plan      -> build targets[], cursor=0
collect   -> best structured source for targets[cursor] (search-first surfaces skip to search)
assess    -> LLM gate over the box's fill-contract; returns one of:
               "resolved"  (filled+sourced)  -> synthesize
               "absent"    (proven no answer)-> mark_absent
               "unresolved"(retry may help)  -> fallback   (if attempts < max)
               "exhausted" (attempts == max) -> mark_absent
fallback  -> web_search tool for targets[cursor]; attempts += 1 -> assess
synthesize-> write draft(box) with source_url -> advance
mark_absent-> write draft(box=absent) -> advance
advance   -> cursor += 1, attempts = 0; more targets? -> collect : persist
persist   -> write to DB (per agent) -> END
```

**Termination guarantees:** every target leaves via `synthesize` or `mark_absent`; `attempts` is bounded by `max_attempts`; LangGraph `recursion_limit` set to `len(targets) * (max_attempts + 3)` as a hard backstop.

### The gate contract (the strict system prompt)
Each agent's system prompt states its page's boxes and the pass condition per box, and requires the model to return a **structured verdict** per box: `{box, verdict: resolved|absent|unresolved, value?, source_url?, reasoning}`. "Fill everything" is explicitly forbidden — the prompt names `absent` as a first-class, correct outcome (e.g. "a competitor with no artifact registry → Artifact Management = none").

## 6. Data-model changes (migrations)

Two small columns; everything else is reused.

1. **`claim.stance`** `VARCHAR(16) NULL` — one of `strong|moderate|weak|none`. The Comparison agent sets it; `comparison_matrix.build_comparison_matrix` reads it directly instead of inferring `comparable`/`no_claim`. Frontend `stanceToStrength` already maps these labels.
2. **`signal.theme_key`** `VARCHAR(64) NULL` — the Industry bucket chosen by the gate. `industry_themes.list_themes` / `theme_detail` prefer it; fall back to `assign_theme` for legacy rows.

Alembic: one new revision after `0006_suppress_self_signals`.

### Provenance without quote-verification
Each **accepted** web result is persisted as a lightweight capture so the existing evidence chain (`Source → RawCapture → Evidence`) and every serializer keep working unchanged:

- One synthetic `Source` per agent, seeded once: `industry_research`, `signals_research`, `comparison_research` (mode `api`, `reliability_grade` `C` for web search / inherit `A` when the structured tier answered).
- Per accepted result: `RawCapture(source=<agent source>, extracted_text=<fetched snippet>, blob_path=<source_url>, provenance="web_search")`.
- Signals attach `SignalEvidence(quote=<synthesized line>, offset=0, match_method="synthesis")`; Claims attach `Evidence(quote=<summary>, offset=0)`.

`match_method="synthesis"` is the honest marker that this quote was written, not verified — distinct from `exact|fuzzy`.

### Retrieval indexing — every finding is retrievable by the Ask chat (REQUIRED)
The Ask feature retrieves over the `Chunk` vector table (pgvector + HNSW, hybrid lexical+semantic + RRF + reliability rerank), preset `ask_ledger → record_types: [claim, signal]`. **`index_chunks()` exists but has no caller today — indexing was never wired.** This design wires it: immediately after each agent persists a `Signal` or `Claim`, it calls

```python
index_chunks(session, chunks_for(finding),
             record_type="signal" | "claim", record_id=finding.id,
             embedder=embedder, entity_id=..., signal_type=...,
             published_at=occurred_at, reliability_grade=...)
```

so the finding — and its `source_url` — is immediately answerable in chat. `index_chunks` already dedups by `content_hash` and batches the embed call, so re-runs are cheap. **No new vector table is needed**; the existing `Chunk` schema and `retrieval.yaml` presets cover it. This is the concrete answer to "every finding must be saved so the chat can retrieve the source."

### Table-alignment summary
Reused as-is: `Signal`, `Claim`, `Evidence`, `SignalEvidence`, `RawCapture`, `Source`, `Chunk`, `Entity`. **Altered:** `+claim.stance`, `+signal.theme_key` (§6, one Alembic revision). **New tables:** none — the vector corpus (`Chunk`) already exists. If, during implementation, a finding type doesn't map cleanly onto `Signal`/`Claim`, prefer *altering* those tables over inventing a parallel store, so one write path feeds both the page and the Ask index.

## 7. Industry agent

**Targets:** the 4 DevSecOps buckets (config, replacing `themes.yaml`). Search-first (no structured tier).

**Boxes per surfaced card:** `standard_chip`, `headline`, `body` (trend + implication), `why_it_matters` (JFrog relevance — required), `theme_key` (bucket), `evidence.source_url` (required).

**Config — `config/industry_buckets.yaml` (NEW), replaces the noisy `themes.yaml`:**

```yaml
buckets:
  - key: supply_chain_vulns
    label: Software Supply-Chain Vulnerabilities & Exploits
    signal_type: security_trust
    include: [malicious package, typosquatting, dependency confusion, repo poisoning,
              secret leakage, poisoned library, npm, pypi, compromised package, CVE exploit]
    exclude: [data breach unrelated to packages]
    jfrog_relevance: "Raises demand for provenance and blocking at the gate — Curation and Xray."
  - key: ai_secops
    label: AI Code-Gen & ML Security
    signal_type: security_trust
    include: [poisoned model, malicious HuggingFace model, model supply chain, MCP security,
              insecure AI-generated code, AI agent exploit, model scanning]
    exclude: [benchmark, quantization, reasoning eval, RAG technique, model release, model quality]
    jfrog_relevance: "Validates JFrog ML / AI Catalog as a secure model registry."
  - key: pipeline_devsecops
    label: Pipeline Security & DevSecOps Platform
    signal_type: product_capability
    include: [CI/CD pipeline attack, reachability analysis, contextual analysis, SBOM automation,
              binary authorization, container runtime security]
    exclude: [general cloud ops, unrelated k8s tutorials]
    jfrog_relevance: "Direct read on the Contextual Analysis value proposition."
  - key: regulation_compliance
    label: Regulatory, Compliance & Standards
    signal_type: market_regulatory
    include: [EU Cyber Resilience Act, CRA, CISA Secure by Design, federal SBOM mandate,
              NVD delay, executive order]
    exclude: [non-software regulation]
    jfrog_relevance: "SBOM/CRA mandates map to AppTrust's evidence story."
```

**Injected per bucket:** `{bucket, include, exclude, instruction}` — instruction = "Return DevSecOps items about this bucket only. Each: headline, trend+implication, JFrog relevance, source_url. `exclude` = out of scope, drop it."

**Gate pass condition:** item maps to exactly one bucket *by reasoning, not keyword*; is about supply-chain/security (the `exclude` list is authoritative — model-quality news is dropped); carries a JFrog relevance line + `source_url`. Fails any → dropped. **Empty is a valid result.**

**Persist:** `Signal(entity=industry, signal_type=bucket.signal_type, theme_key=bucket.key, headline, so_what_product=body, why_it_matters, occurred_at)` + capture stub + `SignalEvidence`. Scores via existing `score()`.

## 8. Signals agent

**Targets:** `(competitor, sub_type)` for the 5 competitors × `{hiring, pricing, funding}`.

**Sub-type → signal_type:** hiring→`talent_org`, pricing→`pricing_packaging`, funding→`corporate_financial` (all exist in `signal_types.yaml`).

**Boxes per card:** `signal_type`, `headline`, `so_what_*` (intent read), `why_it_matters` (relevance line — required), `capability_tags`, `occurred_at` (within recency window), `evidence.source_url` (required).

**Tier 1 structured sources:**
- hiring → Lever/Greenhouse adapter where a source row exists (Sonatype today; add rows for the others where a public ATS token is verified).
- pricing → known pricing-page fetch (config URL per competitor where known).
- funding → none → fails tier 1 immediately → search.

**Injected (worked, Sonatype × hiring):**
```json
{ "competitor":"sonatype", "sub_type":"hiring",
  "structured_source":"https://api.lever.co/v0/postings/sonatype?mode=json",
  "extract":["text","categories.team","categories.location","createdAt","hostedUrl"],
  "relevance_probe":"roles signalling roadmap/GTM shift vs JFrog (enterprise sales, EMEA, security, ML infra)",
  "instruction":"Summarise the hiring pattern as intent; state why it matters to JFrog; cite hostedUrl. If board empty/irrelevant -> fallback." }
```
Fallback: `{ "query":"Sonatype hiring enterprise sales OR security engineer 2026", "sub_type":"hiring" }`.

**Gate pass condition:** record is about *this* competitor and sub-type; dated within window; yields headline + JFrog relevance line + `source_url`. Not usable → fallback → retry → absent (skip target).

**Persist:** `Signal(entity=<competitor>, signal_type=..., headline, so_what_*, why_it_matters, capability_tags, occurred_at)` + capture stub + evidence.

## 9. Comparison agent

**Targets:** the 25 cells `(competitor, dimension)`; 5 competitors × 5 dimensions. Search-first, per-cell loop.

**Boxes per cell:** `stance` (`strong|moderate|weak|none`), `summary` (their solution, one line), `evidence.source_url` (required). Injected read-only: `jfrog_position` (the yardstick).

**Config changes:**
- `config/entities.yaml`: add `snyk`, `aqua`, `checkmarx` (kind `competitor`, tier 2, with aliases). The grid competitor set = GitHub, Sonatype, Snyk, Aqua, Checkmarx. (`gitlab`, `harbor`, `azure_artifacts` remain entities but drop off the grid via a `comparison.competitors` allowlist in config, so we don't delete history.)
- `config/comparison_dimensions.yaml` (NEW) — the 5 columns, decoupled from `jfrog_components.yaml`:

```yaml
dimensions:
  - key: artifact_management
    label: Artifact Management
    probe_keywords: ["<rival> artifact repository", "supported package formats", "deployment model"]
    jfrog_position: "Artifactory — universal, 30+ package types, self-hosted + cloud."
  - key: sca_sbom
    label: SCA / SBOM
    probe_keywords: ["<rival> SCA", "SBOM generation", "dependency scanning"]
    jfrog_position: "Xray + AppTrust — SCA with contextual analysis and SBOM evidence."
  - key: container_security
    label: Container Security
    probe_keywords: ["<rival> container scanning", "image security", "runtime protection"]
    jfrog_position: "Xray container scanning + Advanced Security runtime."
  - key: cicd_integration
    label: CI/CD Integration
    probe_keywords: ["<rival> CI/CD integration", "Jenkins GitHub Actions plugin", "pipeline"]
    jfrog_position: "DRAFT — native across Jenkins/GitLab CI/GitHub Actions/Azure DevOps; build-info + promotion across the pipeline."   # NEEDS APPROVAL
  - key: developer_experience
    label: Developer Experience
    probe_keywords: ["<rival> developer experience", "CLI IDE plugin", "onboarding"]
    jfrog_position: "DRAFT — universal CLI + IDE plugins, single platform; enterprise-oriented rather than solo-dev-first."   # NEEDS APPROVAL
```

**Injected per cell (worked, Sonatype × Artifact Management):**
```json
{ "competitor":"sonatype", "aliases":["Nexus","Nexus Repository"],
  "dimension":"Artifact Management",
  "probe_keywords":["Nexus Repository supported formats","Nexus HA / deployment model"],
  "jfrog_reference":"Artifactory — universal, 30+ package types, self-hosted + cloud",
  "instruction":"Find the competitor's concrete capability in this dimension. Return stance vs the reference, a one-sentence summary, and source_url. No public capability found -> stance='none'." }
```

**Gate pass condition:** `summary` describes a *real* capability; has `source_url`; `stance` justified against `jfrog_reference`. **No evidence → `stance='none'`, never invented** (Snyk/Aqua/Checkmarx correctly resolve to `none` for Artifact Management).

**Persist:** upsert `Claim(subject=jfrog, asserting=<competitor>, dimension=<dim.key>, claim_text=summary, stance=<stance>, claim_type="positioning", reliability_grade)` + capture stub + `Evidence`. Reuses `_claim_for_component`-style lookup for idempotent re-runs.

## 10. Run orchestration

New run kinds in `runs.py` `_RUN_STAGE_JOBS`:

- `industry` → `[("research", "run_industry", {})]`
- `signals` → `[("research", "run_signals", {})]`
- `comparison` → `[("research", "run_comparison", {})]`
- `all` (Today `Run now`) → fans out: starts the three runs **concurrently**, each with its own `run_id`; returns `{run_ids: {industry, signals, comparison}}`.

Each surface run writes its own progress; the frontend polls per surface, so a page lights up the moment *its* run reaches `persist`. Concurrency reuses the existing `ThreadPoolExecutor` pattern from `run_collection`; each agent uses its own `Session`.

**Frontend:**
- `Industry.tsx`, `Signals.tsx`, `Comparison.tsx` each get a `Run this page` button → `POST /runs {kind}` → poll that `run_id`.
- `Today.tsx` `Run now` → `POST /runs {kind:"all"}` → poll three `run_id`s; the existing run banner shows aggregate progress.

## 11. Phase 0 — Removal / clean-slate plan (do this FIRST)

We are on a dedicated branch, so removal is safe and should precede new code — a clean app, not two systems overlapping. Implementation begins by *deleting* the old seeding path, in this order, each step green before the next:

**Ordered removal checklist**
1. **Comparison side-effect** — delete `_bridge_competitor_signal_to_claims` and its call site ([agent_service.py:137](../../../backend/app/services/agent_service.py)); delete the tests asserting the bridge.
2. **Interpret orchestration for the 3 surfaces** — remove `run_interpret`, `_interpret_one`, `_diversify_by_source`, `PER_SOURCE_INTERPRET_CAP` from `worker/jobs.py`; remove `interpret_capture`/`_persist_signal`/`_production_deps` from `agent_service.py`. (See the OSV decision below — this is why it's a decision, not an unconditional delete.)
3. **Interpret graph** — remove `agent/graphs/interpret/` once nothing imports it.
4. **RSS/press seeders** — in `sources.yaml`, remove the industry-noise rows (`hn_*`, tech-press feeds). Delete, don't just disable — this is a clean branch and history lives in git.
5. **`themes.yaml`** — delete; superseded by `industry_buckets.yaml`. Update `industry_themes.py` to read buckets + `theme_key` (drop `assign_theme` keyword routing, or keep only as a legacy fallback).
6. **Run wiring** — replace `_RUN_STAGE_JOBS["manual"]` (collect→interpret→score) with the new per-surface kinds + `all` fan-out (§10).
7. **Dead tests/fixtures** — remove interpret/bridge tests; keep fixtures only where a new agent test reuses them.

**Kept (do not remove):** the Ask corpus + retrieval (`ask_service`, `retrieval/`, `Chunk`), scoring (`materiality`), digest/email, `Entity`/`Source` registry, backfill (already benched).

**OSV — RESOLVED: option (A).** OSV becomes a Tier-1 structured source for a Signals `security_advisory` sub-type (mapping to `signal_type = security_trust`; it also feeds the Industry `supply_chain_vulns` bucket where the advisory is ecosystem-wide rather than competitor-specific). With OSV riding the new agents, **the `interpret` graph and `agent_service.py` orchestration are deleted entirely** in Phase 0 step 2/3 — no leftover pipeline. The `osv` adapter itself is kept and reused as a structured source.

## 12. Performance (speed is a priority)

Carry forward the patterns that made the interpreter fast (commits `diversify interpret across sources`, `de-quadratic quote verification`, the `ThreadPoolExecutor` collection/interpret parallelism):

- **Two-level concurrency.** `Run now` fans out the three agents in parallel (each its own thread + `Session`, mirroring `_run_collection_parallel`). *Within* each agent, targets run through a bounded `ThreadPoolExecutor` (default `max_workers=4`), each target a separate graph invocation with its own `thread_id` and `Session` — the exact shape of `_interpret_one`. 25 comparison cells run concurrently, not serially.
- **The cap is a speed feature, not just a safety valve.** `max_attempts=3` and the `absent` short-circuit bound total LLM+search calls per run; a cell that resolves on attempt 1 spends one gate call.
- **No quadratic scans.** The gate reasons per-box against a fixed contract — never all-pairs. Idempotent upserts (`_claim_for_component`-style lookup) keep re-runs from re-writing unchanged rows.
- **Dedup + batched embeds for free.** `index_chunks` skips work by `content_hash` and batches the embedding call, so re-runs and duplicate findings don't re-embed.
- **Cheap, fast gate model.** The relevance/usable gate is a small, low-latency model (own role in `llm.yaml`, e.g. low `reasoning_effort`, tight `timeout`); the heavier `web_search`-capable model is used only on `collect`/`synthesize`. Config lets each be tuned independently, as today.
- **Config cached in-process** (`load_config`, bucket/dimension YAML) via the existing `lru_cache`.
- **Recursion backstop** (`len(targets) * (max_attempts + 3)`) prevents a pathological loop from hanging a run.

Target: a per-page `Run this page` completes in the low tens of seconds; `Run now` is bounded by the slowest of the three (Comparison), not their sum.

## 13. Testing

- **Unit, per graph:** feed a stub search tool + stub gate; assert (a) resolved box → persisted with source_url; (b) absent box → `none`/dropped, never fabricated; (c) attempts capped at 3; (d) recursion backstop never hit on the happy path.
- **Provenance:** accepted result creates exactly one `RawCapture` under the agent's synthetic `Source`, and evidence chains resolve through existing serializers.
- **Industry relevance:** a "4-bit quantized model" input is dropped by the gate; a "malicious npm package" input is kept and bucketed `supply_chain_vulns`.
- **Comparison absence:** Snyk × Artifact Management → `stance='none'`.
- **Migrations:** `claim.stance`, `signal.theme_key` upgrade/downgrade round-trip.
- **Run fan-out:** `kind:"all"` returns three run_ids and all three reach `done`.

## 14. Open items (draft here, approve before implementation)

1. ~~OSV fold-in~~ — **RESOLVED: (A)**, OSV rides the new agents; `interpret` deleted entirely (§11).
2. **`jfrog_position` for CI/CD Integration and Developer Experience** — drafted in §9, marked `NEEDS APPROVAL`.
3. **Structured pricing-page URLs** per competitor (where known) for the Signals tier-1 pricing source — otherwise pricing is search-only.
4. **Public ATS tokens** for GitHub/Snyk/Aqua/Checkmarx hiring (Greenhouse/Lever) — otherwise hiring is search-only for those four.
5. **Reliability grade for web-search evidence** — proposed `C`; confirm.

## 15. Risks

- **Cost/latency:** worst case ≈ (4 buckets + 15 signal targets + 25 cells) × up to 3 attempts × (LLM + search) per run. Mitigations: the cap, `absent` short-circuits, and Comparison's future stale-only refresh.
- **Lightweight synthesis is unverified** — accepted risk (§3); the `source_url` + `match_method="synthesis"` marker keep it honest.
- **OpenAI web_search availability/quotas** — single vendor dependency; the tiered gate degrades to `absent` rather than crashing if search errors.
