# Agent graphs — ask and research

## Research skeleton (Foundation)

Generic per-target loop shared by Industry, Signals, and Comparison agents:

- Code: `backend/agent/graphs/research/skeleton.py`
- Entry: `run_research(deps)` — plans targets, resolves each to a draft or absent
  (max 3 attempts, falls back to web search on `unresolved`)
- `ResearchDeps` protocol: `plan`, `collect`, `search`, `assess`, `absent_draft`
- Pure graph — no DB; persistence lives in `app/services/research/*_agent.py` and `provenance.py`

## Industry agent

- `run_industry()` → `industry_agent.py` — four buckets from `industry_buckets.yaml`, gate keeps on-topic hits only
- Persist: industry `Signal` + `theme_key`, indexed for Ask

## Signals agent

- `run_signals()` → `signals_agent.py` — targets = allowlisted competitors × sub-types
  (`hiring`, `pricing`, `funding`, `security_advisory`)
- Tiered flow: structured source (Lever/Greenhouse jobs, OSV advisories) → gate → web search fallback
- `structured_for(session)` in app service (DB + adapters); graph deps stay DB-free
- Sub-type → `signal_type`: hiring→`talent_org`, pricing→`pricing_packaging`,
  funding→`corporate_financial`, security_advisory→`security_trust`
- Persist: competitor `Signal` with `why_it_matters`, `capability_tags`, so_what_* lines, indexed

## Comparison agent

- `run_comparison()` → `comparison_agent.py` — 25 cells (5 competitors × 5 dimensions)
- Per-cell search + stance gate; upsert `Claim.stance` + evidence; skip `none` cells

## Web search tool

- Code: `backend/agent/tools/web_search.py`
- `WebSearch.search(query, k)` → `list[SearchHit]`; stubbable via injected client
- Live path uses OpenAI Responses API (`tools=[{"type": "web_search"}]`); requires
  `OPENAI_API_KEY` at runtime (tests use `FakeClient`, no network)
- `_extract_results` walks `response.output`: `message` items → `content` parts of
  type `output_text` → `annotations` of type `url_citation` (`.url`, `.title`,
  optional `.start_index`/`.end_index` for snippet text). Optional `web_search_call`
  items may also carry `action.sources` URLs.

## Grounding guard (research gates)

- Code: `backend/agent/graphs/research/grounding.py`
- Industry, Signals (web-search path), and Comparison `assess()` only resolve when the
  gate's `source_url` is present among the search-hit URLs passed in. Structured-source
  signals (hiring/OSV adapters) skip this check — material has no `SearchHit.url`.

## Ask graph

Flow: `classify_intent → tool_loop (max 4) → grounding_gate → answer | refuse`.

Code: `backend/agent/graphs/ask/graph.py`. Logs under `agent.ask` and
`app.ask_service` (`ask.request.start` / `ask.request.done`, `ask.llm.invoke`).

## Viewing logs

```bash
docker compose logs -f api worker
```

Set verbosity with `LOG_LEVEL=DEBUG` in `.env` (default `INFO`). At DEBUG you also
see which model each `get_model(role)` call builds (`agent.llm`).

## Typical failure signals

| Log line | Meaning |
|---|---|
| `run.failed` | Background run job threw — see traceback |
| `ask.grounding.refuse` | No hits or citations not grounded |
