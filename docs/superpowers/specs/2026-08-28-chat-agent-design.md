# Chat Agent — Planner / Executor / Grounded Drafter

**Status:** design, ready for implementation planning
**Branch:** `jfrog_agent_v2`
**Supersedes:** the single-turn `agent/graphs/ask` graph (deleted once `/ask` is green on the new path)

---

## 1. Goal (and non-goals)

A **working** conversational agent over the competitive-intelligence knowledge base. Three moving parts the user named:

1. A **planner** that reads the user message plus recent conversation and emits a **JSON plan of the run** — which tool to call, in what order, with what arguments, and an **expanded query** (the planner's own restatement of what the user is really asking, with pronouns/entities resolved from context).
2. An **executor** that runs the plan against the existing **hybrid RAG pipeline** to retrieve relevant evidence.
3. A **drafter** that assembles a grounded response **with sources**, using *only* retrieved evidence.

Plus **working memory**: the last 10 interactions, FIFO, held **client-side in browser `localStorage`** and sent with each request. The server is stateless about conversation.

**Non-goals (YAGNI for this MVP):**
- No planner→executor replan loop (static plan only; state is shaped so replan-once is a small later addition).
- No tools beyond RAG retrieve (no live web search, no structured DB lookups in the plan).
- No server-side conversation persistence, no new database tables, no migration.
- "Working, not perfect." Correctness and grounding over breadth.

---

## 2. What already exists (build on, do not rebuild)

- **Hybrid retrieval** — `app/services/retrieval/query.py::search(session, *, query, preset, filters, cfg, embedder) -> list[Hit]`. BM25 lexical + pgvector semantic → RRF fusion → evidentiary rerank → per-document diversity cap. Every knob lives in `config/retrieval.yaml`. `Hit` carries `chunk_id, record_type, record_id, text, score, source_id, reliability_grade`. The retriever **never widens a filter** — an empty prefilter returns nothing.
- **The RAG corpus already contains investigation output.** `app/services/research/provenance.py::index_finding` → `app/services/ingestion/embedding.py::index_chunks` writes claims and signals from the comparison/industry/signals agents into the `chunk` table with metadata (`entity_id, signal_type, published_at, reliability_grade`). **The chat agent retrieves this today; no new chunking work is required.** (Implementation includes one *verification* test that seeded findings are retrievable — not new indexing code.)
- **Grounded answering + source formatting** — `app/services/ask_service.py` shows the pattern: structured-output LLM returning `{answer, citations:[chunk_id]}`, a grounding check that citations ⊆ retrieved chunk ids, and `_format_evidence(session, hits, citations)` which builds source dicts (URL, source name, captured-at, reliability grade, citation object) via `app/services/citation.py`. The drafter reuses this.
- **LLM + embedder helpers** — `agent/llm.py`: `get_model(role)` (config-driven per-role client from `config/llm.yaml`), `get_embedder()`, `prompt(name)` (loads `agent/prompts/<name>.md`). All langgraph lives under `agent/`.

### The dependency rule (must not break)
`app/` must **never** import langgraph. All graph code lives in `agent/`. A service in `app/` (`chat_service.py`) bridges the graph to the FastAPI router and injects a `deps` object; the graph calls `deps.retrieve(...)`, `deps.model`, `deps.format_sources(...)` and never touches SQLAlchemy or `app/` directly. This mirrors `ask_service.py` exactly.

---

## 3. Architecture

New graph `agent/graphs/chat/` with three nodes:

```
START → plan → execute → draft → END
```

`window` (the last-10 transcript) and `message` (raw user turn) arrive in the **initial state** from the request payload — there is no load/persist node, because memory is client-side. `persona` is passed through for tone only; it never changes grounding.

New service `app/services/chat_service.py` bridges the graph to a new router `POST /chat`. `/ask` is reimplemented as a thin call into the same service with `history: []`.

### Module layout
```
backend/agent/graphs/chat/
  __init__.py
  state.py        # ChatState, ChatResult
  graph.py        # plan / execute / draft nodes + build_chat_graph(deps)
backend/agent/prompts/
  chat_plan.md    # planner system prompt (emits JSON plan)
  chat_draft.md   # drafter system prompt (extractive-only, hard rule)
backend/app/services/chat_service.py   # deps + bridge (no langgraph import)
backend/app/routers/chat.py            # POST /chat
backend/app/controllers/chat.py        # thin controller (matches ask.py shape)
```
The `agent/graphs/ask/` package and `app/routers/ask.py`'s dependence on it are removed after `/ask` is green on the chat path. `ask_service._format_evidence` and the `_AskAnswer` grounding pattern are **moved/reused**, not deleted.

---

## 4. State

```python
# agent/graphs/chat/state.py
from dataclasses import dataclass
from typing import TypedDict

@dataclass
class ChatResult:
    answer: str
    sources: list
    grounded: bool
    plan: dict
    reason: str

class ChatState(TypedDict, total=False):
    # inputs
    message: str            # raw user turn
    window: list[dict]      # last-10 transcript: [{"role","content"}], oldest→newest
    persona: str | None
    # planner output
    plan: dict              # the JSON plan (see §5)
    expanded_query: str
    # executor output
    hits: list              # accumulated, deduped retrieved evidence (dicts)
    # drafter output
    answer: str
    citations: list         # chunk ids the drafter cited
    sources: list           # formatted source dicts for the API
    grounded: bool
    reason: str             # refusal reason when not grounded
```

---

## 5. The planner (`plan` node)

One LLM call, `get_model("chat_plan")` with **strict structured output**. Input: the raw `message`, the `window` (formatted as a compact `role: content` transcript), and the list of available presets + filterable fields (from config, so the prompt stays truthful as config evolves). Output schema:

```json
{
  "expanded_query": "context-resolved restatement of the user's question",
  "steps": [
    {
      "tool": "retrieve",
      "query": "sub-query text",
      "preset": "ask_ledger",
      "filters": {"entity": "sonatype", "signal_type": null},
      "reason": "why this step"
    }
  ]
}
```

Rules encoded in the prompt and validated in code:
- `tool` is always `"retrieve"` (the only tool this MVP exposes). Any other value is rejected → treated as a no-hit plan.
- `preset` must be one of the configured retrieval presets (currently `ask_ledger`); unknown preset → rejected.
- `filters.entity` is an entity **slug** the service resolves to `entity_ids` at execution time (the planner never sees numeric ids).
- **1–N steps.** The planner decomposes multi-entity or multi-facet questions into ordered steps (e.g. "JFrog vs Sonatype on security scanning" → one step filtered to each entity). A single-facet question yields one step.
- `expanded_query` resolves pronouns/anaphora against `window` ("how do *they* price it?" → "how does Sonatype price Nexus Repository?"). It is the human-readable record of "the planner expanding the user query by how it understands it."

The planner **does not** answer, retrieve, or invent facts. It only plans. Temperature 0.

**Static plan, no loop:** the plan is produced once; `execute` runs it; `draft` answers. If grounding fails, the agent **refuses** — it does not replan (deferred).

---

## 6. The executor (`execute` node)

Pure orchestration, **no LLM**. For each step in `plan["steps"]`, in order:
1. Resolve `filters.entity` slug → `entity_ids` via `deps` (service-side DB lookup); build the retrieval `filters` dict.
2. Call `deps.retrieve(query=step["query"], preset=step["preset"], filters=...)`.
3. Merge results into `hits`, **deduping by `chunk_id`** (first occurrence wins), preserving order. (Same dedupe `ask`'s `tool_loop` already does.)

A step whose entity filter resolves to nothing is **skipped**, not widened (honors the retriever's no-widening contract). If every step yields zero hits, `hits` is empty and the drafter will refuse.

---

## 7. The drafter (`draft` node) — extractive-only, hard grounding rule

**This is the load-bearing correctness constraint.** `get_model("chat_draft")` with structured output `{answer, citations: [chunk_id]}`.

The node's contract, stated in `chat_draft.md` and enforced in code:

- The drafter may use **only** the text of the retrieved chunks passed to it as numbered evidence. It **must not** add, infer, or "fill in" any fact from its own knowledge. If the evidence does not contain what the user asked for, it **must refuse** ("I don't have grounded evidence on that") rather than guess.
- Every claim in `answer` must be supported by at least one cited chunk. `citations` must be a **subset of the retrieved `chunk_id`s**. Code re-checks this after the call (the `_is_grounded` gate from `ask`); if any citation is outside the retrieved set, or the answer is non-empty with zero citations, the turn is treated as **not grounded** and returned as a refusal. The model cannot talk its way past the code check.
- `answer` combines the evidence into a response that matches the user's query (and the conversation's tone via `persona`/`window`) — synthesis of *retrieved* material is allowed; introduction of *unretrieved* material is not.

`sources` is built from the cited chunks via `deps.format_sources(hits, citations)`, which wraps the reused `_format_evidence` (source URL, name, captured-at, reliability grade, citation object). On refusal, `sources` is empty and `reason` is set; optionally the top 1–3 uncited hits are returned as `nearby_evidence` (as `/ask` already does) so the UI can show "closest I found."

---

## 8. Working memory (client-side)

- The React client keeps `chatHistory` in `localStorage`: an array of turns `{role: "user"|"assistant", content, citations?}`.
- **Windowing / FIFO:** capped at the **last 10 interactions** (10 user↔assistant exchanges). On each new exchange the client pushes the new turns and pops the oldest so the array never exceeds the cap — the "pop the old ones one by one" behavior, entirely in the browser. Nothing persists server-side; clearing the conversation is clearing `localStorage` ("won't save past interactions forever").
- **Request:** `POST /chat { message, history: [...≤10 turns...], persona? }`. The server reads `history` into `ChatState.window`, uses it, stores nothing.
- **Response:** `{ conversation_id?, answer, sources, grounded, plan, reason?, nearby_evidence? }`. `plan` is returned so the JSON plan of the run is visible to the client (demoable). The client appends `{user}` + `{assistant}` to `localStorage` and re-trims to 10.

`conversation_id` is an optional client-generated id echoed back for the client's own bookkeeping/logging; the server does not use it to look anything up.

---

## 9. API & controller

```
POST /chat
  body:  { message: str, history: [{role, content}], persona?: str, conversation_id?: str }
  200:   { answer, sources, grounded, plan, reason?, nearby_evidence?, conversation_id? }
```
- `app/routers/chat.py` → `app/controllers/chat.py::chat(session, body)` → `chat_service.answer_chat(session, message, history, persona)`.
- `/ask` reimplemented: `ask_service.answer_question` calls `chat_service.answer_chat(session, question, history=[], persona=persona)` and maps the result to the existing `/ask` response shape, so the current `/ask` contract and its consumers keep working during the transition. Once verified, the old `ask` graph is deleted.

---

## 10. Config additions

`config/llm.yaml` — two new roles under `calls`:
```yaml
  chat_plan:
    model: <same family as ask>   # temperature: 0, structured output
    temperature: 0
  chat_draft:
    model: <same family as ask>   # temperature: 0, structured output
    temperature: 0
```
No new `config/retrieval.yaml` presets required (the planner uses `ask_ledger`). If, during build, retrieving over collected source documents (not just claims/signals) proves useful, add a preset there — config-only, no code change.

---

## 11. Testing (TDD; offline — LLMs, embedder, retrieval stubbed as elsewhere)

- **Planner** — stub `chat_plan` model returns a canned plan; assert: valid schema, ≥1 step, unknown preset/tool rejected, `expanded_query` present. One test feeds a `window` with an antecedent and asserts the prompt includes the transcript (context is actually passed).
- **Executor** — fake `deps.retrieve` returning overlapping hit sets across two steps; assert dedupe by `chunk_id`, order preserved, empty-filter step skipped.
- **Drafter grounding (the critical tests):**
  - citations ⊆ hits → grounded, sources built from cited chunks only.
  - citation outside hits → refused, empty sources, reason set.
  - non-empty answer with empty citations → refused.
  - empty hits → refused without calling the draft model (or calling and refusing) — assert no fabricated answer is returned.
- **Memory window (client, Vitest/Jest)** — push 12 interactions; assert `localStorage` holds exactly the last 10, oldest dropped, order preserved; request payload carries that window.
- **End-to-end** — stub `chat_plan` + `chat_draft`, real `search` over seeded `chunk` rows (claims/signals from a fixture); assert a grounded answer with real sources, and that `/ask` (history=[]) still returns its legacy shape.
- **Corpus verification** — seed a finding via `index_finding`; assert `search` retrieves it (guards the "investigation findings are in the RAG" assumption).

---

## 12. Implementation & execution protocol (Cursor agent)

Implementation follows the **subagent build protocol** already established in
`docs/superpowers/plans/2026-08-27-00-EXECUTION.md`. The implementation plan produced from this spec (via the writing-plans step) and its own `…-00-EXECUTION.md` reuse that doc's rules:

- **Model assignment:** reasoning/planning/review on **Opus 4.8 (high)** (the orchestrator); every implementer subagent on **Composer 2.5 (fast)**. Set the model explicitly on every dispatch.
- **Test policy:** implementers **write tests as they build but do not run them per task**; run the **full suite once at the end of each plan**; a plan advances only when its suite is green; on failure dispatch a Composer fix subagent (≤3 rounds) before escalating.
- **Wave scheduling:** parallelize only tasks on **disjoint files**; serialize anything sharing a file. For this feature the natural waves are: (1) state + prompts + planner/executor/drafter graph (new files, parallelizable against the service); (2) `chat_service` + router + controller (bridge); (3) `/ask` reimplementation + delete old `ask` graph + `config/llm.yaml` roles (shared-file edits, single implementer); (4) client `localStorage` memory + `/chat` wiring.
- **Autonomy & ledger:** rulings not stalls; record one line per task in a progress ledger; the spec is the binding authority when a plan is ambiguous.

The chat-agent plan is **independent of** the five research-graph plans (they are already built); it only *consumes* their output (the indexed findings) through retrieval.

---

## 13. Definition of done

- `POST /chat` returns a grounded answer with real sources for a question the corpus covers, and a clean **refusal** (no fabrication) for one it doesn't.
- The response includes the **JSON plan** (expanded query + ordered retrieve steps).
- Multi-turn context works: a follow-up with a pronoun is resolved via the client-sent window and answered.
- The client keeps only the **last 10 interactions** in `localStorage`, FIFO.
- The drafter never emits an ungrounded claim — enforced by the code-side citations-⊆-hits gate, covered by tests.
- `/ask` still answers in its legacy shape (history=[]); the old `ask` graph is deleted.
- Full suite (backend + client) green.
