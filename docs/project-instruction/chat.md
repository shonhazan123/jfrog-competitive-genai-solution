# Chat graph — planner / executor / drafter

Graph: `plan → execute → draft`. Code: `backend/agent/graphs/chat/`
(`graph.py`, `state.py`). Prompts: `backend/agent/prompts/chat_plan.md`,
`chat_draft.md`. Bridge: `backend/app/services/chat_service.py` → `POST /chat`
(`backend/app/routers/chat.py` → `controllers/chat.py`).

## Three parts
- **plan** — one `chat_plan` LLM call, structured output. Reads the user turn +
  the client-sent `window` (last-10 transcript) and emits `{expanded_query, steps}`.
  Steps whose `tool != "retrieve"` or whose `preset` is not configured are dropped
  (a fully-rejected plan is a no-hit plan → refusal).
- **execute** — no LLM. Runs each step against `search(preset="ask_ledger")`,
  resolving `filters.entity` slug → `entity_ids` on the service session. A step whose
  entity resolves to nothing is **skipped, never widened**. Hits dedupe by `chunk_id`,
  order preserved.
- **draft** — one `chat_draft` LLM call, extractive-only. `citations` must be a
  non-empty subset of retrieved chunk ids or the turn is a **refusal** (code-enforced,
  not prompt-trusted). Empty hits refuse without calling the model. Sources are built
  from cited chunks via `format_evidence` (reused by `/ask`).

## Memory is client-side
The server is stateless about conversation. `POST /chat` reads `history` into
`ChatState.window`, uses it, stores nothing. The React client keeps the last 10
exchanges in `localStorage` (`client/src/lib/chatHistory.ts`, FIFO) and sends them
each request. Response echoes `plan` (expanded query + steps) for demoability.

## Package boundary
`app/` never imports langgraph. `chat_service` builds the graph via `agent/` and
injects `deps` (retrieve, resolve_entity, plan_model, draft_model, format_sources).
`/ask` is a thin adapter: `ask_service.answer_question` calls
`chat_service.answer_chat(..., history=[])` and maps to the legacy `/ask` shape.
