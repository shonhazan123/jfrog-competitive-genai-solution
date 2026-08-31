# Ask endpoint — now a thin adapter on the chat path

The single-turn `classify_intent → tool_loop → grounding_gate` graph has been
**removed**. `agent/graphs/ask/` no longer exists. `POST /ask` is reimplemented on
the chat agent (see [chat.md](chat.md)).

## Flow

`POST /ask` (`backend/app/routers/ask.py` → `controllers/ask.py`) →
`app/services/ask_service.py::answer_question`, which calls
`chat_service.answer_chat(session, question, history=[], persona=persona)` and maps
the chat result back to the **legacy `/ask` response shape** so existing consumers
keep working:

- `grounded`, `answer`, `evidence` (= chat `sources`), `refusal_reason` (= chat
  `reason` when not grounded), `nearby_evidence`, `question`, `persona`.

Because `history=[]`, `/ask` is exactly a one-turn chat with no conversation window.
Grounding is enforced the same way as chat: the drafter's citations must be a
non-empty subset of retrieved chunk ids, or the turn is a refusal (see chat.md §draft).

## Package boundary

`app/` never imports `langgraph` / `langchain` / `openai` literals (enforced by
`tests/test_boundaries.py`). `ask_service.py` imports only `agent.log` and
`app.services.chat_service`; the graph is built inside `chat_service` via `agent/`.
