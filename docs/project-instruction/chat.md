# Chat graph — planner / executor / drafter

Graph: `plan → execute → draft`. Code: `backend/agent/graphs/chat/`
(`graph.py`, `state.py`). Prompts: `backend/agent/prompts/chat_plan.md`,
`chat_draft.md`. Bridge: `backend/app/services/chat_service.py` → `POST /chat`
(`backend/app/routers/chat.py` → `controllers/chat.py`).

## Three parts
- **plan** — one `chat_plan` LLM call, structured output. Reads the user turn +
  the client-sent `window` (last-10 transcript) and emits `{expanded_query, steps}`.
  Steps whose `tool != "retrieve"` or whose `preset` is not configured are dropped
  (a fully-rejected plan is a no-hit plan → refusal). Valid steps are capped at
  `_MAX_STEPS` (5) to bound retrieval fan-out (`graph.py`).
- **execute** — no LLM. Runs each step against `search(preset="ask_ledger")` **with
  an embedder** so both the lexical *and* semantic (pgvector) arms run — passing no
  embedder makes retrieval lexical-only and paraphrased questions return zero hits.
  Resolves `filters.entity` slug → `entity_ids` on the service session; a step whose
  entity resolves to nothing is **skipped, never widened**. Hits dedupe by `chunk_id`,
  order preserved. The shared loop is `execute_steps(deps, steps)` in `graph.py`
  (used by both the graph and the streaming path).
- **draft** — one `chat_draft` LLM call, extractive-only. `citations` must be a
  non-empty subset of retrieved chunk ids or the turn is a **refusal** (code-enforced,
  not prompt-trusted). Empty hits refuse without calling the model. Sources are built
  from cited chunks via `format_evidence` (reused by `/ask`). Note: the gate is
  all-or-nothing — a single citation id not present in the hit set refuses the whole
  answer (`reason='citations_not_in_hits'`).

## Citations link to the origin URL
Each `Chunk` carries a `url` column — the live internet URL the finding was gathered
from (set at index time from `capture.blob_path`; see `index_finding`). Retrieval
returns it (`Hit.url` → hit dict), and `format_evidence` uses it as the citation
`source_url`, deriving the display name from the URL host when there is no `Source`
row (research chunks have `source_id = NULL`). Without this the citation URL was empty
and the client link resolved back to the app itself. Migration `0009_chunk_url` adds
the column and backfills existing chunks via
`chunk → signal_evidence/evidence → raw_capture.blob_path`. `SourceLink` (client)
additionally refuses to render a non-`http(s)` href as a live link.

## Latency & models
`chat_plan` and `chat_draft` run on `gpt-5-mini` (planner `reasoning_effort: minimal`,
drafter `low`) — full `gpt-5` reasoning cost ~15–45s per turn on planning alone. Typical
turn is now ~3s plan + ~3s retrieve (one embedding call) + ~8s draft.

## Streaming
`POST /chat/stream` returns Server-Sent Events for perceived latency (the draft is the
dominant wait). `answer_chat_stream` (in `chat_service`) runs plan + `execute_steps`,
then streams the drafter's answer tokens and finally emits the grounding verdict:
- `data: {"type":"plan", "expanded_query", "steps"}`
- `data: {"type":"token", "text"}` — repeated answer deltas
- `data: {"type":"done", "grounded", "answer", "sources", "reason", "nearby_evidence", "conversation_id"}`

Streaming uses a **TypedDict** structured-output schema (`_ChatDraftDict`) because
`with_structured_output` only streams partial JSON for dict/JSON-schema outputs, not
Pydantic. Tokens stream **before** the grounding gate runs, so the terminal `done`
event is authoritative: on a failed gate the client discards the provisional text and
shows the refusal. The non-streaming `POST /chat` is unchanged.

## Memory is client-side
The server is stateless about conversation. `POST /chat` reads `history` into
`ChatState.window`, uses it, stores nothing. The React client keeps the last 10
exchanges in `localStorage` (`client/src/lib/chatHistory.ts`, FIFO) and sends them
each request. Response echoes `plan` (expanded query + steps) for demoability. The
Ask page (`client/src/pages/Ask.tsx`) consumes `/chat/stream` via
`api.postChatStream`, rendering tokens live and committing the exchange to history on
the `done` event (only when grounded).

## Package boundary
`app/` never imports langgraph. `chat_service` builds the graph via `agent/` and
injects `deps` (retrieve, resolve_entity, plan_model, draft_model, draft_stream_model,
embedder, format_sources). `/ask` is a thin adapter: `ask_service.answer_question`
calls `chat_service.answer_chat(..., history=[])` and maps to the legacy `/ask` shape.
The streaming path reuses the graph's `execute_steps` / `_is_grounded` / `_valid_steps`
/ `_transcript` helpers so retrieval and grounding stay identical across both paths.
