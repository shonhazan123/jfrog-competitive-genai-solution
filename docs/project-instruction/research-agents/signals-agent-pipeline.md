# Signals agent — pipeline flow

**Scope:** Competitor signals (hiring, pricing, funding, security advisories). Runs inside
the three-agent thread pool (see [00-three-agent-orchestration.md](./00-three-agent-orchestration.md)).

Unlike Industry and Comparison, Signals uses a **tiered collect path**: structured API/ATS/OSV
sources first, then web search fallback.

## Activation order

```mermaid
sequenceDiagram
    participant Ctrl as runs._run_surface
    participant Job as run_signals
    participant SK as run_research
    participant Dep as SignalsDeps
    participant Struct as structured_for
    participant Adpt as Lever/Greenhouse/OSV
    participant WS as web_search
    participant Gate as LLM gate
    participant DB as Postgres

    Ctrl->>Job: jobs.run_signals(progress)
    Job->>Job: get_model("gate") → SignalCard
    Job->>Job: SignalsDeps(build_targets(), structured, search_fn, gate)
    Job->>SK: run_research(deps, progress)
    SK->>Dep: plan() → 20 targets
    loop Each target in parallel pool
        Dep->>Struct: collect(target)
        alt hiring or security_advisory + enabled source
            Struct->>Adpt: adapter.collect(source, fetcher)
            Adpt-->>Dep: list of API record dicts
        else pricing/funding or no source
            Struct-->>Dep: None
            Dep->>WS: search via _query(target, attempt)
            WS-->>Dep: SearchHit[]
        end
        Dep->>Gate: research_signals prompt + material JSON
        Gate-->>Dep: SignalCard
        Dep->>Dep: grounding check on source_url
    end
    SK-->>Job: list of drafts
    Job->>DB: persist_signals(session, drafts)
    DB-->>Job: signals_items count
```

## Target planning

**Functions:** `build_targets()` → `signals_agent.py`; `SignalsDeps.plan()` → `signals/deps.py`

| Input config | Function |
|---|---|
| `config/competitors.yaml` | allowlist slugs |
| `config/entities.yaml` | names + aliases via `load_competitors()` |

**20 targets** = 5 competitors × 4 sub-types:

| sub_type | signal_type (DB) | Structured collect? |
|---|---|---|
| `hiring` | `talent_org` | Yes — Lever or Greenhouse `Source` on entity |
| `pricing` | `pricing_packaging` | No — web search only |
| `funding` | `corporate_financial` | No — web search only |
| `security_advisory` | `security_trust` | Yes — OSV adapter on entity |

Each target dict: `{competitor, name, aliases, sub_type, signal_type}`.

## Information gathering — tiered flow

```mermaid
flowchart TD
    T["Target competitor × sub_type"]
    COL["SignalsDeps.collect → structured_for(target)"]
    DBQ["SessionLocal per call: query Entity + Source"]
    ADP{"Adapter?"}
    LEV["LeverAdapter.collect"]
    GH["GreenhouseAdapter.collect"]
    OSV["OsvAdapter.collect"]
    NONE["return None"]
    SEARCH["SignalsDeps.search → web_search(_query, k=6)"]
    MAT["material: API dicts OR SearchHit[]"]

    T --> COL --> DBQ --> ADP
    ADP -->|hiring + lever| LEV
    ADP -->|hiring + greenhouse| GH
    ADP -->|security_advisory + osv| OSV
    ADP -->|no source / pricing / funding| NONE
    LEV & GH & OSV --> MAT
    NONE --> SEARCH --> MAT
```

### Structured collect (thread-safe)

**Functions:** `structured_for()` → `_structured_collect()` → `signals_agent.py`

- Production: `structured_for()` with **no session** — each parallel worker opens its own
  `SessionLocal()` inside `collect()`
- Queries `Entity` by competitor slug, finds enabled `Source` with matching `adapter`
- Converts adapter records via `_api_record_to_dict()` → `{external_id, title, body, occurred_at, url, extra}`

### Web search fallback

**Function:** `_query()` → `signals_agent.py` (injected as `search_fn` into `SignalsDeps`)

| sub_type | Query pattern |
|---|---|
| hiring | `{name} careers {aliases} enterprise sales OR security engineer` |
| pricing | `{name} pricing plans per-seat` |
| funding | `{name} funding round OR acquisition 2026` |
| security_advisory | `{name} {aliases} security advisory CVE vulnerability` |

Broadened on retry via `broaden_query()` in `query.py`.

## LLM gate — what gets injected

**Function:** `SignalsDeps.assess()` → `backend/agent/graphs/research/signals/deps.py`

1. Prompt: `agent/prompts/research_signals.md`
2. JSON **DATA** payload:

```json
{
  "competitor": "Sonatype",
  "aliases": ["..."],
  "sub_type": "hiring",
  "material": [
    {"title", "url", "snippet"}           // SearchHit path
    // OR
    {"external_id", "title", "body", "url", ...}  // structured path
  ]
}
```

3. Structured output: `SignalCard` — `usable`, `headline`, `so_what`, `why_it_matters`,
   `tags`, `source_url`
4. Resolve when: `usable && source_url && why_it_matters`
5. **Grounding:**
   - Web-search material: `source_url_grounded()` — URL must be in hit list
   - Structured material: grounding **skipped** (`hit_urls()` returns `None` → grounded=True)

## Draft shapes

**Resolved:**

```python
{
  "competitor": "sonatype",
  "signal_type": "talent_org",
  "headline": "...",
  "so_what": "...",
  "why_it_matters": "...",
  "tags": ["..."],
  "source_url": "https://..."
}
```

**Absent:**

```python
{"competitor": "...", "sub_type": "...", "absent": True}
```

Absent drafts are **skipped** in `persist_signals()` (`if draft.get("absent"): continue`).

## Persistence to database

**Functions:** `persist_signals()` → `signals_agent.py`; called inside `run_signals()` on one
`SessionLocal()` session (serial writes after parallel research).

```mermaid
flowchart TD
    DRAFTS["drafts excluding absent=True"]
    P1["Pass 1: record_finding per draft"]
    RC["RawCapture under signals_research source"]
    P2["Pass 2: dedupe_items by entity_slug+signal_type+window"]
    SIG["Signal on competitor entity"]
    SE["SignalEvidence per cluster member"]
    IDX["index_finding record_type=signal"]
    TAGS["capability_tags from gate tags"]

    DRAFTS --> P1 --> RC --> P2 --> SIG
    SIG --> SE --> IDX
    SIG --> TAGS
```

| Column / table | Content |
|---|---|
| `signal.entity_id` | Competitor entity (not industry) |
| `signal.signal_type` | Mapped from sub_type |
| `signal.headline` | Gate output |
| `signal.so_what_*` | Same `so_what` for sales/product/exec |
| `signal.why_it_matters` | Gate output |
| `signal.capability_tags` | Gate `tags` |
| `signal.cluster_key` | SHA256 of `{slug}:{signal_type}:{headline}` |
| `raw_capture.blob_path` | Real source URL (ATS job page, OSV advisory, or web hit) |
| `chunk` | Embedded `so_what` text for Ask |

Materiality scores computed via `score()` in `materiality.py` at persist time.

## Return value

`run_signals()` → `{"signals_items": n}` — count of new `Signal` rows after dedup.

## Function index

| Function | Path |
|---|---|
| `run_signals` | `backend/app/services/research/signals_agent.py` |
| `build_targets` / `_query` / `_structured_collect` | same |
| `structured_for` | same |
| `persist_signals` | same |
| `SignalsDeps` / `_as_json` | `backend/agent/graphs/research/signals/deps.py` |
| `source_url_grounded` / `hit_urls` | `backend/agent/graphs/research/grounding.py` |
| `LeverAdapter` / `GreenhouseAdapter` / `OsvAdapter` | `backend/app/services/collection/apis/` |
| `load_competitors` | `backend/app/services/research/competitors.py` |
| `run_research` | `backend/agent/graphs/research/skeleton.py` |
