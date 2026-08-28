> **Note:** The single-turn `classify_intent → tool_loop → grounding_gate` graph has been **replaced** by the chat path (see [chat.md](chat.md)); `/ask` now calls `chat_service.answer_chat(history=[])`.

# Ask graph — routing and state

Graph: `classify_intent → tool_loop (max 4) → grounding_gate → answer | refuse`.

Code: `backend/agent/graphs/ask/` (`graph.py`, `state.py`).

## Hits live on deps, not in checkpointed state

Retrieved hits accumulate on the **deps object** (`deps.accumulated_hits`), never
in LangGraph state. `MemorySaver` serializes checkpointed state with msgpack and
cannot encode custom hit objects. `AskState` stays JSON-serializable:
`question`, `filters`, `answer`, `citations`, `refused`, `reason`,
`tool_iterations`.

Do not put `_Hit` / retrieval objects (or a `hits` list of them) onto `AskState`.

## Grounding gate routes on `refused`

`_after_grounding` reads the real `refused` field on `AskState`. Do **not** route
on a `_route` key — LangGraph strips keys that are not in the TypedDict, so a
transient `_route` always falls through to refuse.

## Empty retrieval refuses without the model

If `deps.accumulated_hits` is empty after the tool loop, `grounding_gate` sets
`refused=True` and returns. It does **not** call `deps.model.answer`. The model
runs only when there is at least one hit.

## Package boundary

`app/` never imports `langgraph` / `openai` literals. `POST /ask`
(`backend/app/routers/ask.py` → `controllers/ask.py`) bridges through
`backend/app/services/ask_service.py`, which is the only HTTP-side importer of
`agent.graphs.ask.graph`. Interpret still goes through `agent_service.py` (worker
jobs); that is a different graph and a different caller.
