# ARCHITECTURE — Code-level design

| | |
|---|---|
| **Status** | Shipped — research-engine architecture |
| **Date** | 30 August 2026 |
| **Author** | Shon Hazan |
| **Related** | [PRD.md](./PRD.md) — problem and requirements · [API_CONTRACT.md](./API_CONTRACT.md) — HTTP surface · [archive/v1-interpret-approach/](./archive/v1-interpret-approach/) — the superseded first design |

> **This document describes the system as built.** An earlier design centred on a
> per-capture *Interpret graph* with a verbatim verification gate, element-first
> ingestion, human-in-the-loop quarantine, and Wayback backfill. That approach was
> accurate but too slow to produce usable intelligence in the time budget, and was
> replaced by the per-surface **research engines** described here. The full v1
> design record lives in
> [`docs/archive/v1-interpret-approach/`](./archive/v1-interpret-approach/).

**Governing rule applied throughout: no magic numbers in code.** Every threshold,
weight, cap and window is declared in YAML under `config/`, validated by a Pydantic
model at boot, seeded into Postgres, and editable at runtime through a cached
accessor invalidated by a `config_version` bump.

---

## 1. Repository layout

```
jfrog-ci/
├── docker-compose.yml            db · api · worker · client
├── .env.example
├── config/                       ◀ the modularity surface (YAML → seeded to DB)
│   ├── entities.yaml             competitors, tiers, aliases
│   ├── sources.yaml              URLs, kind, mode, grade, cadence
│   ├── signal_types.yaml         taxonomy + trigger terms
│   ├── routing.yaml              signal_type × persona matrix
│   ├── materiality.yaml          scoring weights, modifiers, interrupt tiers
│   ├── watchlist.yaml            free-text terms of current interest
│   ├── industry_buckets.yaml     industry-agent topic buckets
│   ├── comparison_matrix.yaml    competitors × dimensions grid
│   ├── chunking.yaml             element grouping budgets (retrieval write path)
│   ├── retrieval.yaml            RRF, rerank boosts, diversity
│   └── llm.yaml                  one block per LLM call (role → model/params)
│
├── docs/                         PRD.md · ARCHITECTURE.md · API_CONTRACT.md
│   ├── project-instruction/      ◀ operational flow (update when code changes)
│   └── archive/                  ◀ superseded v1 design record (docs only)
│
├── backend/
│   ├── app/                      ◀ MVC. Never imports langgraph / openai literals.
│   │   ├── main.py · settings.py
│   │   ├── models/               SQLAlchemy ORM
│   │   ├── schemas/ serializers/ Pydantic DTOs / response shaping
│   │   ├── routers/              APIRouter path declarations only
│   │   ├── controllers/          request handling, validation, orchestration
│   │   └── services/
│   │       ├── collection/       fetcher · robots · ratelimit · feeds · apis
│   │       ├── normalization/    parsers · elements · tracked_page
│   │       ├── detection/        hashing · structural_diff
│   │       ├── scoring/          materiality · config_loader
│   │       ├── ingestion/embed   chunk · embed · index          (RAG write path)
│   │       ├── retrieval/        hybrid RRF query               (RAG read path)
│   │       ├── delivery/         digest assembly · email · templates
│   │       ├── research/         industry_agent · signals_agent · comparison_agent
│   │       │                     provenance · competitors      (persist side)
│   │       ├── snapshot.py       live tracked-page diff → claim/version
│   │       ├── chat_service.py   ◀ POST /ask bridge → agent.graphs.chat.graph
│   │       └── maintenance.py    reset_findings
│   │
│   ├── agent/                    ◀ the only package importing LLM libraries
│   │   ├── graphs/
│   │   │   ├── research/         skeleton + industry/ · signals/ · comparison/
│   │   │   │                     grounding.py · query.py
│   │   │   └── chat/             graph.py · state.py   (LangGraph Ask agent)
│   │   ├── tools/                web_search.py
│   │   ├── prompts/              research_* · chat_plan · chat_draft · ask
│   │   ├── llm.py                model clients (role → ChatOpenAI), embedder
│   │   └── log.py
│   │
│   └── worker/                   scheduler.py · jobs.py · main.py
│
├── client/src/                   components · pages · api · hooks
└── tests/                        pytest suite (real Postgres via testcontainers)
```

### The dependency rule

**`app → agent`, never the reverse.** The agent accepts plain data and returns plain
data; the persist side lives in `app/services/research/*`. The isolation is
mechanically checkable:

```bash
grep -rn "openai\|langchain\|langgraph" backend/app/    # returns nothing
```

This is the privilege-isolation boundary against indirect prompt injection made a
five-second check rather than a claim.

---

## 2. Framework placement

LangGraph is used in **one place**: the **chat/Ask graph**, where branching on a
grounding outcome and refusal-as-an-edge earn the graph metaphor.

The **research engines do not use LangGraph.** A per-surface run is a *map over
independent targets with a concurrency limit* — a bounded `ThreadPoolExecutor`, not
a graph. `backend/agent/graphs/research/skeleton.py` is that loop. Collection
(`httpx` + `feedparser`), scheduling (APScheduler), the snapshot diff (pure
functions), scoring (arithmetic) and email (Jinja) are likewise plain code.

**LangChain, thin:** `ChatOpenAI(...).with_structured_output(Model, strict=True)`
for the gates, `langchain-postgres` `PGVector` for the index, OpenAI embeddings.
Raw requests and responses are logged independently of the framework.

### Two postures, by data trust

The design principle that outlived the v1 pivot: **the model that reads untrusted
web content must not be the model that decides what happens next.**

- **Research gates** read search hits and structured records (attacker-influenceable)
  and emit *only* a closed structured verdict — no tools bound, `temperature 0`,
  schema-locked. They classify; they cannot act.
- **The chat/Ask agent** has a bounded reasoning loop and read-only retrieval tools,
  because it reads only the vetted ledger — never raw web content. The grounding
  gate runs *after* the loop, which is why it is a custom graph rather than a
  prebuilt ReAct agent.

---

## 3. The research engines

Three per-surface engines share one skeleton (`run_research(deps)`), which plans
targets and resolves each — concurrently, under `RESEARCH_MAX_WORKERS` — to a draft
or an absent draft. Per-target failures are isolated: one target's DNS error yields
its absent draft and the run continues.

| Engine | Targets | Sources | Persist |
|---|---|---|---|
| **Industry** (`run_industry`) | four buckets from `industry_buckets.yaml` | web search, on-topic gate | industry `Signal` + `theme_key` |
| **Signals** (`run_signals`) | competitors × sub-types (hiring, pricing, funding, security_advisory) | structured (Lever/Greenhouse jobs, OSV advisories) → gate → web-search fallback | competitor `Signal` + `why_it_matters`, `so_what_*`, `capability_tags` |
| **Comparison** (`run_comparison`) | competitors × dimensions (`comparison_matrix.yaml`) | per-cell web search + stance gate | `Claim` + `stance` + evidence |

Each resolved finding is classified individually — a release note with 40 bullets is
not one signal — and most candidates return `no_signal` and are dropped. **A low
`no_signal` rate is a defect, not good coverage:** a model that must return
something will invent something, so the gate schemas bless the empty case.

### The gate (`grounding.py`)

Industry, Signals (web-search path) and Comparison only resolve a finding when the
gate's cited `source_url` is present among the search-hit URLs passed in.
Structured-source signals (Lever/Greenhouse/OSV) skip this check — the record *is*
the source. The gate is a `with_structured_output(strict=True)` call over a closed
enum built from the seeded entity registry, so **the model cannot name a competitor
absent from configuration** — hallucinated entities fail schema validation.

### Provenance and the evidence model (read this honestly)

`provenance.record_finding` stores each finding as a `RawCapture` under a synthetic
`internal://{agent}_research` source, with the real hit URL on `capture.blob_path`
(`provenance = "web_search"`). Serializers resolve citation links from `blob_path`.

**What the stored quote actually is.** For the research (web-search) path, the stored
evidence quote is the model's **grounded synthesis of the search result**, carried
with the real source URL — `signal_evidence.match_method = 'synthesis'`. It is *not*
a verbatim span cut from a re-fetched page. The grounding is at the OpenAI-web-search
level (the URL is a real citation the search returned); the local verbatim-verification
gate from v1 is **not** exercised on this path. This is a known limitation the system
owns openly — re-introducing verbatim verification for the research path is tracked in
§9, not claimed as done.

The **live snapshot path** (`snapshot.py`, §6) is the exception: it cuts evidence
verbatim from the fetched page (`quote = source_text[offset:offset+len]`) and records
`ClaimVersion` deltas over time. It produces the tracked-comparison claims, not the
research signals.

**NUL / control-byte sanitization.** Postgres text columns reject `0x00`. Web-search
text and its LLM syntheses can carry NUL or other C0 bytes, so
`provenance.sanitize_text` strips them (keeping tab/newline/CR) at every write
boundary.

---

## 4. The ledger

```python
Signal(entity_id, subject_entity_id, signal_type, headline, occurred_at,
       capability_tags, cluster_key, corroboration_count,
       score_sales/product/exec, score_breakdown, so_what_*, why_it_matters,
       handling, theme_key, status)
Claim(subject_entity_id, asserting_entity_id, claim_text, claim_type,
      capability_tags, dimension, stance, reliability_grade, first/last_seen)
SignalEvidence(signal_id, capture_id, quote, quote_offset, match_method)
Evidence(claim_id, capture_id, quote, quote_offset)
```

**Comparison convention:** a comparison `Claim` carries `subject_entity_id = jfrog`
(the reference point) and `asserting_entity_id = the competitor` being described.
Filter the grid by `asserting_entity`, not `subject_entity`.

---

## 5. Retrieval (RAG) — kept from v1, used by chat/Ask

Findings are chunked and embedded on persist (`index_finding`), into one table
carrying both a `vector(1536)` HNSW index and a `tsvector` GIN index. Retrieval is a
shared deterministic SQL service on the `app` side, reached by the agent through a
port:

```
① structured pre-filter  →  ② lexical ‖ semantic  →  ③ RRF fusion
                          →  ④ deterministic rerank (reliability · primary · recency)
                          →  ⑤ diversity cap  →  ⑥ sibling expansion
```

The pre-filter is the highest-leverage stage; RRF fuses incomparable score scales by
rank; the rerank encodes *evidence quality*, not topical similarity. **The retriever
is allowed to return nothing** — it never widens a filter to avoid an empty result,
and an empty result is what triggers the chat graph's refusal edge. All parameters
live in `config/retrieval.yaml`. (HNSW is the production-correct default for a
daily-growing corpus; the choice costs nothing now and is not revisited.)

---

## 6. Collection and the live snapshot path

`worker/jobs.run_collection` sweeps enabled sources by mode, grouped by domain, one
Session per thread:

```python
match source.mode:
    case "feed":     novelty by entry id      (feedparser)
    case "api":      novelty by record id     (OSV / Greenhouse / Lever / HN adapters)
    case "snapshot": structural diff vs last  (snapshot.collect_snapshot_source)
```

`feed`/`api` sources ask *"is this entry new?"* — a unique-constraint lookup, not a
diff. `snapshot` sources (tracked comparison pages) run the verbatim extract/diff
pipeline in `snapshot.py`: parse the page into comparison rows, diff against the last
stored `PageSnapshot`, and turn each material row change into a `Claim` update plus a
`ClaimVersion`, with evidence cut verbatim from the page.

---

## 7. Scoring, digests, delivery

**Materiality** (`scoring/materiality.py`) is a pure function, every coefficient from
`materiality.yaml`: a persona-routed base times modifiers (subject-is-JFrog for sales,
entity tier, corroboration, watchlist hits, recency decay, source grade).
`ScoreBreakdown.parts` is persisted and rendered on the card — the arithmetic is the
UI, which is what makes the score tunable rather than merely visible.

**Digest assembly** (`delivery/assembly.py`) selects per persona: eligible by
threshold, sorted by score, diversity-capped per entity, truncated to an absolute
budget. Three deterministic **interrupt tiers** break the daily cadence
(positioning about JFrog · high-CVSS security · M&A). `silent_entities` is a
first-class output — *"no material change for Harbor — checked N times"* — because
negative reporting is what makes the positive reports believable.

**Delivery** renders the digest (Jinja) and, when SMTP is configured, emails it;
otherwise it is available at `GET /digests/{persona}`.

---

## 8. The chat/Ask graph

```
classify_intent → plan → execute (retrieve, bounded) → grounding_gate → answer | refuse
```

`backend/agent/graphs/chat/graph.py`, a real LangGraph `StateGraph`. `POST /ask` never
imports the graph from a router: `routers/ask.py → controllers → chat_service.py →
agent.graphs.chat`. Retrieval hits accumulate on `deps`, not in checkpointed state
(msgpack cannot encode them). The grounding gate routes on `refused`: an empty
retrieval set sets `refused=True` and **does not call the model** — refusal is an
edge, not a prompt instruction.

---

## 9. Known gaps / still to be designed

Stated openly rather than papered over — these are the "what's missing" backlog:

- **Verbatim verification for the research path.** Research evidence is grounded
  synthesis, not a re-fetched-and-cut span (§3). Re-introducing the v1 gate for at
  least the comparison grid is the highest-value hardening.
- **Corroboration / clustering.** `corroboration_count` is effectively always 1;
  one event arriving from several framings is not yet collapsed into one signal.
- **`occurred_at` extraction.** Event dates are not reliably parsed, so recency
  decay is currently a weak signal.
- **Competitor coverage.** Configured tier-2 competitors (GitLab, Harbor, Azure
  Artifacts) can come back empty; "silent" must be distinguished from "starved" so
  negative reporting stays trustworthy.
- **Digest end-to-end.** Assembly and delivery exist but need a demonstrated run and
  the sales/exec `so_what_*` filled for every signal.
- **Observability and cost control** — per-stage token accounting and funnel metrics.
