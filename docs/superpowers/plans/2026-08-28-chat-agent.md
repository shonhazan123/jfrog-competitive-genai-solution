# Chat Agent (Planner / Executor / Grounded Drafter) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working conversational agent over the CI knowledge base — a JSON-plan **planner**, a no-LLM **executor** over the existing hybrid RAG pipeline, and an extractive-only **drafter** that grounds every claim in retrieved evidence or refuses — plus client-side FIFO working memory, with `/ask` reimplemented on the same path.

**Architecture:** A new LangGraph package `agent/graphs/chat/` runs `START → plan → execute → draft → END`. A new stateless service `app/services/chat_service.py` bridges the graph to `POST /chat`, injecting a `deps` object (retrieve, entity resolution, two models, source formatting) so `app/` never imports langgraph. Conversation memory is the client's `localStorage` (last 10 exchanges), sent on each request as `history`. `/ask` becomes a thin call into `chat_service.answer_chat(..., history=[])`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, LangGraph, LangChain-OpenAI (structured output), pgvector/pytest (`testcontainers`), React + TypeScript + Vitest + Testing Library.

## Global Constraints

- **Package boundary (hard):** `app/` must never `import langchain`, `import langgraph`, or `import openai` (enforced by `tests/test_boundaries.py`). All graph/LLM code lives in `agent/`. The graph calls only `deps.*`; it never touches SQLAlchemy or `app/`.
- **Grounding is code-enforced, not prompt-trusted:** `citations` must be a non-empty subset of the retrieved `chunk_id`s. Any citation outside the retrieved set, or a non-empty answer with zero citations, is a **refusal**. The model cannot talk past this check.
- **Retriever never widens a filter:** an entity filter that resolves to nothing means that step is **skipped**, not broadened. Empty prefilter → zero hits (existing `search` contract).
- **Two new deterministic LLM roles:** `chat_plan` and `chat_draft`, both `temperature: 0`, structured output. Same model family as `ask` (`gpt-5`).
- **Only tool is `retrieve`; only preset is `ask_ledger`.** Unknown tool/preset → step rejected (a rejected-all plan is a no-hit plan → drafter refuses).
- **Working memory is client-side only.** Server is stateless about conversation: reads `history` into state, stores nothing. Cap = **last 10 exchanges**, FIFO.
- **Execution protocol (from `docs/superpowers/plans/2026-08-27-00-EXECUTION.md`):** implementers **write tests as they build but DO NOT run them per task**. Run the **full suite once at the end of each wave/plan**; a wave advances only when green. Orchestrator on **Opus 4.8 (high)**; every implementer subagent on **Composer 2.5 (fast)** — set the model explicitly on every dispatch.
- **Backend tests** live in top-level `tests/` (NOT `backend/tests/`). They import from the `backend/` packages (`agent.*`, `app.*`) and use the session-scoped pgvector `session` fixture in `tests/conftest.py`. `search` runs **lexical-only** (no `embedder`) exactly as `ask_service` uses it today.
- **DRY, YAGNI, TDD, frequent commits.** No new DB tables, no migration, no server-side persistence, no replan loop.

---

## File Structure

**New backend files**
- `backend/agent/graphs/chat/__init__.py` — package marker.
- `backend/agent/graphs/chat/state.py` — `ChatState` (TypedDict), `ChatResult` (dataclass).
- `backend/agent/graphs/chat/graph.py` — `plan` / `execute` / `draft` nodes + `build_chat_graph(deps)`.
- `backend/agent/prompts/chat_plan.md` — planner system prompt (emits JSON plan).
- `backend/agent/prompts/chat_draft.md` — drafter system prompt (extractive-only, hard rule).
- `backend/app/services/chat_service.py` — deps builder + `answer_chat(...)` + `format_evidence(...)` (moved from `ask_service`). No langgraph import.
- `backend/app/routers/chat.py` — `POST /chat`.
- `backend/app/controllers/chat.py` — thin controller (matches `ask.py` shape).

**Modified backend files**
- `backend/app/main.py` — register `chat.router`.
- `backend/app/services/ask_service.py` — reimplemented as a thin adapter over `chat_service.answer_chat(..., history=[])`; drops the old graph/model plumbing.
- `config/llm.yaml` — add `chat_plan` and `chat_draft` roles.
- **Deleted after `/ask` is green:** `backend/agent/graphs/ask/graph.py`, `backend/agent/graphs/ask/state.py`, `backend/agent/graphs/ask/__init__.py`.

**New/modified client files**
- `client/src/lib/chatHistory.ts` — `localStorage` window helpers (load / append / trim to 10). **New.**
- `client/src/lib/chatHistory.test.ts` — window FIFO tests. **New.**
- `client/src/api/endpoints.ts` — add `chatPath()`.
- `client/src/api/types.ts` — add `ChatTurn`, `ChatRequest`, `ChatResponse`; extend `AskRequest` with `history`.
- `client/src/api/client.ts` — add `postChat(...)`; keep `postAsk` fixture behavior.
- `client/src/pages/Ask.tsx` — use `localStorage` window, call `postChat`, persist + re-trim.

**New backend test files**
- `tests/test_chat_graph.py` — planner / executor / drafter graph tests (stubbed deps).
- `tests/test_chat_service.py` — e2e over seeded chunks (real `search`, stubbed models), corpus verification, `/ask` legacy shape.

---

## Waves (dispatch order)

- **Wave 1 (parallelizable, disjoint new files):** Task 1 (state), Task 2 (prompts), Task 3 (graph) — Task 3 consumes Task 1's `ChatState`, so dispatch Task 1 first, then Tasks 2+3 in parallel. Then run the suite (`tests/test_chat_graph.py`).
- **Wave 2 (single implementer, new files + one shared edit):** Task 4 (`chat_service`), Task 5 (router + controller + `main.py` registration). Then run the suite (`tests/test_chat_service.py`).
- **Wave 3 (single implementer, shared-file edits):** Task 6 (`config/llm.yaml` roles), Task 7 (`/ask` reimplementation), Task 8 (delete old `ask` graph). Then run the **full backend suite**.
- **Wave 4 (single implementer, client):** Task 9 (`chatHistory` lib), Task 10 (`/chat` wiring in api + Ask page). Then run the **client suite**.

---

## Task 1: Chat graph state

**Files:**
- Create: `backend/agent/graphs/chat/__init__.py`
- Create: `backend/agent/graphs/chat/state.py`
- Test: covered by `tests/test_chat_graph.py` (Task 3)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ChatState(TypedDict, total=False)` with keys: `message: str`, `window: list[dict]`, `persona: str | None`, `plan: dict`, `expanded_query: str`, `hits: list`, `answer: str`, `citations: list`, `sources: list`, `grounded: bool`, `reason: str`, `nearby_evidence: list`, `conversation_id: str | None`.
  - `ChatResult` dataclass: `answer: str`, `sources: list`, `grounded: bool`, `plan: dict`, `reason: str`.

- [ ] **Step 1: Create the package marker**

Create `backend/agent/graphs/chat/__init__.py` empty:

```python
```

(Empty file — it only marks the package. Create it with zero bytes.)

- [ ] **Step 2: Write `state.py`**

Create `backend/agent/graphs/chat/state.py`:

```python
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
    window: list[dict]      # last-10 transcript: [{"role","content"}], oldest->newest
    persona: str | None
    conversation_id: str | None
    # planner output
    plan: dict              # the JSON plan (see chat_plan.md)
    expanded_query: str
    # executor output
    hits: list              # accumulated, deduped retrieved evidence (dicts)
    # drafter output
    answer: str
    citations: list         # chunk ids the drafter cited
    sources: list           # formatted source dicts for the API
    grounded: bool
    reason: str             # refusal reason when not grounded
    nearby_evidence: list   # up to 3 uncited hit texts on refusal
```

- [ ] **Step 3: Commit**

```bash
git add backend/agent/graphs/chat/__init__.py backend/agent/graphs/chat/state.py
git commit -m "feat(chat): add chat graph state (ChatState, ChatResult)"
```

---

## Task 2: Planner and drafter prompts

**Files:**
- Create: `backend/agent/prompts/chat_plan.md`
- Create: `backend/agent/prompts/chat_draft.md`
- Test: prompt-content assertions live in `tests/test_chat_graph.py` (Task 3)

**Interfaces:**
- Consumes: nothing.
- Produces: two prompt files loaded by `agent.llm.prompt("chat_plan")` / `prompt("chat_draft")`. The planner prompt is appended with `DATA:\n{json}` carrying `message`, `transcript`, `presets`, `filter_fields`. The drafter prompt is appended with `DATA:\n{json}` carrying `question`, `evidence` (numbered `{id,text}`), `persona`, `transcript`.

- [ ] **Step 1: Write `chat_plan.md`**

Create `backend/agent/prompts/chat_plan.md`:

```markdown
You are the PLANNER for a competitive-intelligence chat agent. You do NOT answer
questions and you do NOT invent facts. You only produce a JSON plan describing how
to retrieve evidence for the user's latest message.

You are given:
- `message`: the user's latest turn.
- `transcript`: the recent conversation as `role: content` lines, oldest first.
  Use it to resolve pronouns and anaphora (e.g. "how do they price it?").
- `presets`: the retrieval presets you may use. Use ONLY these values.
- `filter_fields`: the filter keys you may set (e.g. `entity`, `signal_type`).

Produce:
- `expanded_query`: a single self-contained restatement of what the user is really
  asking, with every pronoun and implied entity resolved from the transcript. This is
  the human-readable record of how you understood the question.
- `steps`: 1..N ordered retrieval steps. Each step:
  - `tool`: ALWAYS the literal string "retrieve".
  - `query`: the sub-query text to search for.
  - `preset`: one of `presets`.
  - `filters`: an object with `entity` (an entity slug like "sonatype" or "jfrog",
    or null) and `signal_type` (or null). Never use a numeric id.
  - `reason`: one short sentence on why this step exists.

Rules:
- Decompose multi-entity or multi-facet questions into ordered steps — e.g.
  "JFrog vs Sonatype on security scanning" becomes one step filtered to each entity.
- A single-facet question yields exactly one step.
- If the user asks about a specific competitor, set `filters.entity` to that slug.
- Do not answer, retrieve, summarize, or add facts. Plan only.
```

- [ ] **Step 2: Write `chat_draft.md`**

Create `backend/agent/prompts/chat_draft.md`:

```markdown
You are the DRAFTER for a competitive-intelligence chat agent. You write a grounded
answer using ONLY the numbered evidence provided. This is a hard rule.

You are given:
- `question`: the resolved question to answer.
- `evidence`: a numbered list of chunks, each `{ "id": <chunk id>, "text": <quote> }`.
- `persona`: optional tone hint (sales / product / exec). Tone only — never changes grounding.
- `transcript`: recent conversation for tone/context only.

Rules:
- Use ONLY the text in `evidence`. Do NOT add, infer, or "fill in" any fact from your
  own knowledge. Synthesis of the RETRIEVED material is allowed; introducing
  UNRETRIEVED material is not.
- Every factual claim in `answer` must be supported by at least one cited chunk.
- `citations` must be a subset of the `evidence` ids you actually used.
- If the evidence does not contain what the user asked for, REFUSE: set `answer` to a
  short "I don't have grounded evidence on that." and leave `citations` empty. Do not guess.
- Match the user's question and the conversation's tone. Keep it concise.

Return `{ "answer": <string>, "citations": [<chunk id>, ...] }`.
```

- [ ] **Step 3: Commit**

```bash
git add backend/agent/prompts/chat_plan.md backend/agent/prompts/chat_draft.md
git commit -m "feat(chat): add planner and drafter prompts"
```

---

## Task 3: Chat graph (plan / execute / draft nodes + build_chat_graph)

**Files:**
- Create: `backend/agent/graphs/chat/graph.py`
- Test: `tests/test_chat_graph.py`

**Interfaces:**
- Consumes: `ChatState` from `agent.graphs.chat.state` (Task 1). A `deps` object exposing:
  - `deps.presets -> list[str]` (e.g. `["ask_ledger"]`)
  - `deps.filter_fields -> list[str]` (e.g. `["entity", "signal_type"]`)
  - `deps.plan_model.plan(message: str, transcript: str, presets: list[str], filter_fields: list[str]) -> dict` returning `{"expanded_query": str, "steps": [{"tool","query","preset","filters":{"entity","signal_type"},"reason"}]}`
  - `deps.draft_model.draft(question: str, hits: list[dict], persona: str | None, transcript: str) -> dict` returning `{"answer": str, "citations": list[str]}`
  - `deps.retrieve(*, query: str, preset: str, filters: dict) -> list[dict]` where each dict has at least `"id"` (chunk id as str) and `"text"`
  - `deps.resolve_entity(slug: str) -> list[int]`
  - `deps.format_sources(hits: list[dict], citations: list[str]) -> list[dict]`
- Produces: `build_chat_graph(deps)` → a compiled LangGraph (no checkpointer). Node helpers `plan`, `execute`, `draft`. `_hit_id`, `_is_grounded`, `_transcript`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_chat_graph.py`:

```python
import pytest

from agent.graphs.chat.graph import build_chat_graph


class _StubPlanModel:
    def __init__(self, plan):
        self._plan = plan
        self.last_call = None

    def plan(self, message, transcript, presets, filter_fields):
        self.last_call = {
            "message": message,
            "transcript": transcript,
            "presets": presets,
            "filter_fields": filter_fields,
        }
        return self._plan


class _StubDraftModel:
    def __init__(self, answer, citations):
        self._answer = answer
        self._citations = citations
        self.called = False

    def draft(self, question, hits, persona, transcript):
        self.called = True
        return {"answer": self._answer, "citations": list(self._citations)}


def _make_deps(*, plan, draft_answer="", draft_citations=None,
               retrieve_map=None, entity_map=None):
    draft_citations = draft_citations or []
    retrieve_map = retrieve_map or {}
    entity_map = entity_map or {}

    class Deps:
        presets = ["ask_ledger"]
        filter_fields = ["entity", "signal_type"]

        def __init__(self):
            self.plan_model = _StubPlanModel(plan)
            self.draft_model = _StubDraftModel(draft_answer, draft_citations)
            self.retrieve_calls = []

        def retrieve(self, *, query, preset, filters):
            self.retrieve_calls.append({"query": query, "preset": preset, "filters": filters})
            return list(retrieve_map.get(query, []))

        def resolve_entity(self, slug):
            return list(entity_map.get(slug, []))

        def format_sources(self, hits, citations):
            cited = set(citations)
            return [{"n": i + 1, "quote": h["text"]}
                    for i, h in enumerate(h for h in hits if h["id"] in cited)]

    return Deps()


def _hit(chunk_id, text):
    return {"id": chunk_id, "text": text}


def test_planner_output_is_recorded_and_transcript_is_passed():
    plan = {
        "expanded_query": "How does Sonatype price Nexus Repository?",
        "steps": [{"tool": "retrieve", "query": "sonatype nexus pricing",
                   "preset": "ask_ledger", "filters": {"entity": "sonatype", "signal_type": None},
                   "reason": "price question"}],
    }
    deps = _make_deps(plan=plan, retrieve_map={"sonatype nexus pricing": [_hit("c1", "Nexus pricing tiers")]},
                      draft_answer="Nexus has tiered pricing.", draft_citations=["c1"],
                      entity_map={"sonatype": [42]})
    graph = build_chat_graph(deps)
    result = graph.invoke({
        "message": "how do they price it?",
        "window": [{"role": "user", "content": "Tell me about Sonatype Nexus"}],
        "persona": None,
    })
    assert result["plan"]["expanded_query"] == "How does Sonatype price Nexus Repository?"
    assert result["expanded_query"] == "How does Sonatype price Nexus Repository?"
    # the window transcript was actually handed to the planner
    assert "Sonatype Nexus" in deps.plan_model.last_call["transcript"]
    assert deps.plan_model.last_call["presets"] == ["ask_ledger"]


def test_unknown_tool_or_preset_step_is_rejected_to_a_no_hit_plan():
    plan = {
        "expanded_query": "q",
        "steps": [
            {"tool": "delete_everything", "query": "x", "preset": "ask_ledger",
             "filters": {"entity": None, "signal_type": None}, "reason": "bad tool"},
            {"tool": "retrieve", "query": "y", "preset": "unknown_preset",
             "filters": {"entity": None, "signal_type": None}, "reason": "bad preset"},
        ],
    }
    deps = _make_deps(plan=plan)
    graph = build_chat_graph(deps)
    result = graph.invoke({"message": "hi", "window": [], "persona": None})
    # every step rejected -> executor retrieves nothing -> refusal, no draft model call
    assert deps.retrieve_calls == []
    assert result["grounded"] is False
    assert deps.draft_model.called is False


def test_executor_dedupes_by_chunk_id_and_preserves_order():
    plan = {
        "expanded_query": "q",
        "steps": [
            {"tool": "retrieve", "query": "q1", "preset": "ask_ledger",
             "filters": {"entity": None, "signal_type": None}, "reason": "a"},
            {"tool": "retrieve", "query": "q2", "preset": "ask_ledger",
             "filters": {"entity": None, "signal_type": None}, "reason": "b"},
        ],
    }
    deps = _make_deps(
        plan=plan,
        retrieve_map={
            "q1": [_hit("c1", "one"), _hit("c2", "two")],
            "q2": [_hit("c2", "two-dup"), _hit("c3", "three")],
        },
        draft_answer="ans", draft_citations=["c1"],
    )
    graph = build_chat_graph(deps)
    result = graph.invoke({"message": "m", "window": [], "persona": None})
    ids = [h["id"] for h in result["hits"]]
    assert ids == ["c1", "c2", "c3"]  # first occurrence wins, order preserved


def test_executor_skips_a_step_whose_entity_resolves_to_nothing():
    plan = {
        "expanded_query": "q",
        "steps": [{"tool": "retrieve", "query": "q1", "preset": "ask_ledger",
                   "filters": {"entity": "ghost", "signal_type": None}, "reason": "a"}],
    }
    deps = _make_deps(plan=plan, retrieve_map={"q1": [_hit("c1", "one")]}, entity_map={})
    graph = build_chat_graph(deps)
    result = graph.invoke({"message": "m", "window": [], "persona": None})
    assert deps.retrieve_calls == []          # skipped, never widened
    assert result["grounded"] is False


def test_grounded_answer_builds_sources_from_cited_chunks_only():
    plan = {
        "expanded_query": "q",
        "steps": [{"tool": "retrieve", "query": "q1", "preset": "ask_ledger",
                   "filters": {"entity": None, "signal_type": None}, "reason": "a"}],
    }
    deps = _make_deps(
        plan=plan,
        retrieve_map={"q1": [_hit("c1", "cited"), _hit("c2", "uncited")]},
        draft_answer="Grounded answer.", draft_citations=["c1"],
    )
    graph = build_chat_graph(deps)
    result = graph.invoke({"message": "m", "window": [], "persona": None})
    assert result["grounded"] is True
    assert result["answer"] == "Grounded answer."
    assert [s["quote"] for s in result["sources"]] == ["cited"]


def test_citation_outside_hits_is_refused_with_empty_sources():
    plan = {
        "expanded_query": "q",
        "steps": [{"tool": "retrieve", "query": "q1", "preset": "ask_ledger",
                   "filters": {"entity": None, "signal_type": None}, "reason": "a"}],
    }
    deps = _make_deps(
        plan=plan,
        retrieve_map={"q1": [_hit("c1", "cited")]},
        draft_answer="Fabricated.", draft_citations=["c9"],
    )
    graph = build_chat_graph(deps)
    result = graph.invoke({"message": "m", "window": [], "persona": None})
    assert result["grounded"] is False
    assert result["sources"] == []
    assert result["reason"]


def test_non_empty_answer_with_no_citations_is_refused():
    plan = {
        "expanded_query": "q",
        "steps": [{"tool": "retrieve", "query": "q1", "preset": "ask_ledger",
                   "filters": {"entity": None, "signal_type": None}, "reason": "a"}],
    }
    deps = _make_deps(
        plan=plan,
        retrieve_map={"q1": [_hit("c1", "cited")]},
        draft_answer="I know this from training.", draft_citations=[],
    )
    graph = build_chat_graph(deps)
    result = graph.invoke({"message": "m", "window": [], "persona": None})
    assert result["grounded"] is False
    assert result["sources"] == []


def test_empty_hits_refuses_without_calling_the_draft_model():
    plan = {
        "expanded_query": "q",
        "steps": [{"tool": "retrieve", "query": "q1", "preset": "ask_ledger",
                   "filters": {"entity": None, "signal_type": None}, "reason": "a"}],
    }
    deps = _make_deps(plan=plan, retrieve_map={"q1": []},
                      draft_answer="should not run", draft_citations=["c1"])
    graph = build_chat_graph(deps)
    result = graph.invoke({"message": "m", "window": [], "persona": None})
    assert result["grounded"] is False
    assert deps.draft_model.called is False
    assert result["answer"] and "grounded" in result["answer"].lower()
```

- [ ] **Step 2: (Per execution protocol, do NOT run yet — write the implementation next.)**

- [ ] **Step 3: Write `graph.py`**

Create `backend/agent/graphs/chat/graph.py`:

```python
from langgraph.graph import END, START, StateGraph

from agent.graphs.chat.state import ChatState
from agent.log import get_logger, step

logger = get_logger("agent.chat")

_REFUSAL = "I don't have grounded evidence to answer that."


def _hit_id(hit) -> str:
    return hit["id"] if isinstance(hit, dict) else hit.id


def _is_grounded(citations: list, hits: list) -> bool:
    if not citations:
        return False
    hit_ids = {_hit_id(h) for h in hits}
    return all(c in hit_ids for c in citations)


def _transcript(window: list[dict]) -> str:
    lines = []
    for turn in window or []:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _valid_steps(plan: dict, presets: list[str]) -> list[dict]:
    steps = []
    for s in plan.get("steps", []) or []:
        if s.get("tool") != "retrieve":
            continue
        if s.get("preset") not in presets:
            continue
        if not s.get("query"):
            continue
        steps.append(s)
    return steps


def plan_node(state: ChatState, deps) -> dict:
    message = state["message"]
    transcript = _transcript(state.get("window", []))
    step(logger, "chat.plan.start", message=message)
    raw = deps.plan_model.plan(message, transcript, deps.presets, deps.filter_fields)
    steps = _valid_steps(raw, deps.presets)
    expanded = raw.get("expanded_query") or message
    plan = {"expanded_query": expanded, "steps": steps}
    step(logger, "chat.plan.done", steps=len(steps), expanded_query=expanded)
    return {"plan": plan, "expanded_query": expanded}


def execute_node(state: ChatState, deps) -> dict:
    plan = state.get("plan", {})
    hits: list = []
    seen: set = set()
    for s in plan.get("steps", []):
        filters = s.get("filters") or {}
        entity_slug = filters.get("entity")
        retrieval_filters: dict = {}
        if entity_slug:
            entity_ids = deps.resolve_entity(entity_slug)
            if not entity_ids:
                step(logger, "chat.execute.skip", entity=entity_slug, reason="unresolved")
                continue
            retrieval_filters = {"entity_ids": entity_ids}
        new_hits = deps.retrieve(query=s["query"], preset=s["preset"], filters=retrieval_filters)
        for h in new_hits:
            hid = _hit_id(h)
            if hid not in seen:
                seen.add(hid)
                hits.append(h)
    step(logger, "chat.execute.done", hits=len(hits))
    return {"hits": hits}


def draft_node(state: ChatState, deps) -> dict:
    hits = state.get("hits", [])
    if not hits:
        step(logger, "chat.draft.refuse", reason="no_hits")
        return {
            "answer": _REFUSAL,
            "citations": [],
            "sources": [],
            "grounded": False,
            "reason": "No grounded evidence to support an answer.",
            "nearby_evidence": [],
        }
    question = state.get("expanded_query") or state["message"]
    transcript = _transcript(state.get("window", []))
    result = deps.draft_model.draft(question, hits, state.get("persona"), transcript)
    citations = result.get("citations", [])
    answer = result.get("answer", "")
    if _is_grounded(citations, hits):
        sources = deps.format_sources(hits, citations)
        step(logger, "chat.draft.done", citations=len(citations), sources=len(sources))
        return {
            "answer": answer,
            "citations": citations,
            "sources": sources,
            "grounded": True,
            "reason": "",
            "nearby_evidence": [],
        }
    step(logger, "chat.draft.refuse", reason="citations_not_in_hits")
    cited = set(citations)
    nearby = [{"text": h["text"]} for h in hits if _hit_id(h) not in cited][:3]
    return {
        "answer": _REFUSAL,
        "citations": [],
        "sources": [],
        "grounded": False,
        "reason": "Answer is not supported by grounded evidence.",
        "nearby_evidence": nearby,
    }


def build_chat_graph(deps):
    builder = StateGraph(ChatState)
    builder.add_node("plan", lambda s: plan_node(s, deps))
    builder.add_node("execute", lambda s: execute_node(s, deps))
    builder.add_node("draft", lambda s: draft_node(s, deps))
    builder.add_edge(START, "plan")
    builder.add_edge("plan", "execute")
    builder.add_edge("execute", "draft")
    builder.add_edge("draft", END)
    return builder.compile()
```

- [ ] **Step 4: Commit**

```bash
git add backend/agent/graphs/chat/graph.py tests/test_chat_graph.py
git commit -m "feat(chat): add plan/execute/draft graph with code-enforced grounding"
```

---

## Wave 1 gate

- [ ] **Run the chat-graph suite and confirm green**

Run: `pytest tests/test_chat_graph.py -v`
Expected: PASS (8 tests). On failure, dispatch a Composer fix subagent with the failing output (≤3 rounds).

---

## Task 4: chat_service (deps + answer_chat + format_evidence)

**Files:**
- Create: `backend/app/services/chat_service.py`
- Test: `tests/test_chat_service.py`

**Interfaces:**
- Consumes: `build_chat_graph` (Task 3); `agent.llm.get_model` / `prompt`; `app.services.retrieval.query.search`; `app.services.config_overrides.current_config`; `app.models.registry.Entity, Source`; `app.services.citation` helpers; `app.serializers.common.fmt_ts`.
- Produces:
  - `format_evidence(session, hits: list[dict], citations: list[str]) -> list[dict]` (moved verbatim from `ask_service`).
  - `answer_chat(session, message: str, history: list[dict] | None = None, persona: str | None = None, conversation_id: str | None = None) -> dict` returning `{conversation_id, answer, sources, grounded, plan, reason, nearby_evidence}`.
  - `_ChatFilters`, `_ChatStep`, `_ChatPlan`, `_ChatDraft` pydantic models.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_chat_service.py`:

```python
from datetime import UTC, datetime

import pytest

from app.models.delivery import Chunk
from app.models.registry import Entity, Source


@pytest.fixture
def seeded_corpus(session):
    jf = Entity(slug="jfrog", name="JFrog", kind="self", tier=1)
    sona = Entity(slug="sonatype", name="Sonatype", kind="competitor", tier=1)
    session.add_all([jf, sona])
    session.flush()
    src = Source(
        key="sonatype_pricing", entity_id=sona.id, url="https://sonatype.com/pricing",
        kind="html_page", mode="snapshot", reliability_grade="A", is_primary=True,
        check_frequency_minutes=1440, last_checked_at=datetime.now(UTC),
    )
    session.add(src)
    session.flush()
    session.add_all([
        Chunk(record_type="claim", record_id=1, source_id=src.id, entity_id=sona.id,
              text="Sonatype Nexus Repository is offered in tiered pricing plans.",
              prefix="pricing", reliability_grade="A", content_hash="chat-sona-pricing-1"),
        Chunk(record_type="signal", record_id=2, source_id=src.id, entity_id=sona.id,
              text="Nexus enterprise tier adds SSO and support SLAs.",
              prefix="pricing enterprise", reliability_grade="B", content_hash="chat-sona-pricing-2"),
    ])
    session.flush()
    return {"jfrog": jf, "sonatype": sona, "source": src}


class _CannedPlan:
    def __init__(self, plan):
        self._plan = plan

    def plan(self, message, transcript, presets, filter_fields):
        return self._plan


class _CitesFirstHit:
    def draft(self, question, hits, persona, transcript):
        return {"answer": "Nexus uses tiered pricing.", "citations": [hits[0]["id"]]}


def _patch_models(monkeypatch, plan, draft):
    from app.services import chat_service
    monkeypatch.setattr(chat_service, "_build_plan_model", lambda: _CannedPlan(plan))
    monkeypatch.setattr(chat_service, "_build_draft_model", lambda: draft)


def test_answer_chat_returns_grounded_answer_with_real_sources(session, seeded_corpus, monkeypatch):
    from app.services.chat_service import answer_chat

    plan = {"expanded_query": "How is Sonatype Nexus priced?",
            "steps": [{"tool": "retrieve", "query": "nexus pricing tiers", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "pricing"}]}
    _patch_models(monkeypatch, plan, _CitesFirstHit())
    out = answer_chat(session, "how is it priced?",
                      history=[{"role": "user", "content": "Tell me about Sonatype Nexus"}])
    assert out["grounded"] is True
    assert out["answer"] == "Nexus uses tiered pricing."
    assert len(out["sources"]) == 1
    assert out["sources"][0]["source_url"] == "https://sonatype.com/pricing"
    assert out["plan"]["expanded_query"] == "How is Sonatype Nexus priced?"


def test_answer_chat_refuses_cleanly_when_corpus_lacks_it(session, seeded_corpus, monkeypatch):
    from app.services.chat_service import answer_chat

    plan = {"expanded_query": "Sonatype 2099 revenue forecast",
            "steps": [{"tool": "retrieve", "query": "sonatype 2099 revenue forecast", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "forecast"}]}

    class _Fabricator:
        def draft(self, question, hits, persona, transcript):
            return {"answer": "It will be $1B.", "citations": ["not-a-real-id"]}

    _patch_models(monkeypatch, plan, _Fabricator())
    out = answer_chat(session, "what is their 2099 revenue?")
    assert out["grounded"] is False
    assert out["sources"] == []
    assert out["reason"]


def test_seeded_finding_is_retrievable_by_the_chat_path(session, seeded_corpus, monkeypatch):
    """Corpus verification: findings written via index_finding are retrievable."""
    from app.services.research import provenance
    from app.services.chat_service import answer_chat

    class FakeEmbedder:
        def embed(self, texts):
            return [[0.0] * 1536 for _ in texts]

    monkeypatch.setattr(provenance, "get_embedder", lambda: FakeEmbedder())
    provenance.index_finding(
        session, record_type="signal", record_id=999, text="Sonatype announced a malware firewall.",
        entity_id=seeded_corpus["sonatype"].id, signal_type="security_trust",
        published_at=datetime.now(UTC), reliability_grade="B",
    )
    session.flush()

    plan = {"expanded_query": "Sonatype malware firewall",
            "steps": [{"tool": "retrieve", "query": "sonatype malware firewall", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "security"}]}

    class _CitesMalware:
        def draft(self, question, hits, persona, transcript):
            match = next(h for h in hits if "malware firewall" in h["text"])
            return {"answer": "Sonatype shipped a malware firewall.", "citations": [match["id"]]}

    _patch_models(monkeypatch, plan, _CitesMalware())
    out = answer_chat(session, "did sonatype ship a malware firewall?")
    assert out["grounded"] is True
    assert any("malware firewall" in s["quote"] for s in out["sources"])
```

- [ ] **Step 2: Write `chat_service.py`**

Create `backend/app/services/chat_service.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agent.graphs.chat.graph import build_chat_graph
from agent.llm import get_model, prompt as load_prompt
from agent.log import get_logger, step
from app.models.registry import Entity, Source
from app.serializers.common import fmt_ts
from app.services.citation import DeliveryRecord, build_citation, citation_to_dict
from app.services.config_overrides import current_config
from app.services.retrieval.query import search

logger = get_logger("app.chat_service")


class _ChatFilters(BaseModel):
    entity: str | None = None
    signal_type: str | None = None


class _ChatStep(BaseModel):
    tool: str
    query: str
    preset: str
    filters: _ChatFilters = Field(default_factory=_ChatFilters)
    reason: str = ""


class _ChatPlan(BaseModel):
    expanded_query: str
    steps: list[_ChatStep] = Field(default_factory=list)


class _ChatDraft(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)


def _build_plan_model():
    llm = get_model("chat_plan").with_structured_output(_ChatPlan, strict=True)

    class Adapter:
        def plan(self, message: str, transcript: str, presets: list[str],
                 filter_fields: list[str]) -> dict[str, Any]:
            payload = {"message": message, "transcript": transcript,
                       "presets": presets, "filter_fields": filter_fields}
            prompt_text = load_prompt("chat_plan") + "\n\nDATA:\n" + json.dumps(payload, default=str)
            step(logger, "chat.llm.plan", message=message)
            result = llm.invoke(prompt_text)
            return result.model_dump()

    return Adapter()


def _build_draft_model():
    llm = get_model("chat_draft").with_structured_output(_ChatDraft, strict=True)

    class Adapter:
        def draft(self, question: str, hits: list, persona: str | None,
                  transcript: str) -> dict[str, Any]:
            evidence = [{"id": str(h["id"]), "text": h["text"]} for h in hits]
            payload = {"question": question, "evidence": evidence,
                       "persona": persona, "transcript": transcript}
            prompt_text = load_prompt("chat_draft") + "\n\nDATA:\n" + json.dumps(payload, default=str)
            step(logger, "chat.llm.draft", question=question, evidence_chunks=len(evidence))
            result = llm.invoke(prompt_text)
            return {"answer": result.answer, "citations": result.citations}

    return Adapter()


def format_evidence(session: Session, hits: list[dict], citations: list[str]) -> list[dict]:
    sources = {source.id: source for source in session.query(Source).all()}
    cited = set(citations)
    evidence: list[dict] = []
    n = 1
    for hit in hits:
        hit_id = str(hit["id"])
        if hit_id not in cited:
            continue
        source = sources.get(hit.get("source_id"))
        fetched_at = source.last_checked_at if source and source.last_checked_at else datetime.now(UTC)
        record = DeliveryRecord(
            source_name=source.key.replace("_", " ").title() if source else "unknown",
            source_url=source.url if source else "",
            fetched_at=fetched_at,
            provenance="extracted",
            reliability_grade=hit.get("reliability_grade") or (source.reliability_grade if source else "C"),
        )
        evidence.append(
            {
                "n": n,
                "quote": hit["text"],
                "source_url": source.url if source else "",
                "source_name": source.key.replace("_", " ").title() if source else "unknown",
                "captured_at": fmt_ts(fetched_at),
                "reliability_grade": hit.get("reliability_grade") or (source.reliability_grade if source else "C"),
                "credibility_score": 2,
                "citation": citation_to_dict(build_citation(record)),
            }
        )
        n += 1
    return evidence


def _build_deps(session: Session):
    cfg = current_config()
    rcfg = cfg.retrieval

    class Deps:
        presets = list(rcfg.presets.keys())
        filter_fields = ["entity", "signal_type"]
        _plan_model = None
        _draft_model = None

        @property
        def plan_model(self):
            if self._plan_model is None:
                self._plan_model = _build_plan_model()
            return self._plan_model

        @property
        def draft_model(self):
            if self._draft_model is None:
                self._draft_model = _build_draft_model()
            return self._draft_model

        def resolve_entity(self, slug: str) -> list[int]:
            entity = session.query(Entity).filter_by(slug=slug).one_or_none()
            return [entity.id] if entity else []

        def retrieve(self, *, query: str, preset: str, filters: dict) -> list[dict]:
            hits = search(session, query=query, preset=preset, filters=filters, cfg=cfg)
            return [
                {
                    "id": str(hit.chunk_id),
                    "text": hit.text,
                    "source_id": hit.source_id,
                    "reliability_grade": hit.reliability_grade,
                }
                for hit in hits
            ]

        def format_sources(self, hits: list[dict], citations: list[str]) -> list[dict]:
            return format_evidence(session, hits, citations)

    return Deps()


def answer_chat(session: Session, message: str, history: list[dict] | None = None,
                persona: str | None = None, conversation_id: str | None = None) -> dict:
    """Bridge POST /chat to the chat graph without importing langgraph in app/."""
    step(logger, "chat.request.start", message=message, persona=persona,
         history=len(history or []))
    deps = _build_deps(session)
    graph = build_chat_graph(deps)
    try:
        result = graph.invoke({
            "message": message,
            "window": history or [],
            "persona": persona,
        })
    except Exception:
        logger.exception("chat.request.failed message=%r", message)
        raise
    grounded = bool(result.get("grounded"))
    step(logger, "chat.request.done", grounded=grounded,
         sources=len(result.get("sources", [])))
    return {
        "conversation_id": conversation_id,
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "grounded": grounded,
        "plan": result.get("plan", {}),
        "reason": result.get("reason") or None,
        "nearby_evidence": result.get("nearby_evidence", []),
    }
```

Note: the two graph-facing model builders are module-level (`_build_plan_model`, `_build_draft_model`) so tests can `monkeypatch` them without a live OpenAI client; the deps call them lazily so no model is constructed unless a plan/draft actually runs.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/chat_service.py tests/test_chat_service.py
git commit -m "feat(chat): add chat_service bridge (deps, answer_chat, format_evidence)"
```

---

## Task 5: /chat router + controller + registration

**Files:**
- Create: `backend/app/routers/chat.py`
- Create: `backend/app/controllers/chat.py`
- Modify: `backend/app/main.py` (register router)
- Test: `tests/test_chat_service.py` (add an endpoint test below)

**Interfaces:**
- Consumes: `chat_service.answer_chat` (Task 4).
- Produces: `POST /chat` accepting `{ message, history?, persona?, conversation_id? }` → `{ answer, sources, grounded, plan, reason?, nearby_evidence?, conversation_id? }`. Controller `chat.chat(session, message, history, persona, conversation_id) -> dict`.

- [ ] **Step 1: Write the failing endpoint test**

Append to `tests/test_chat_service.py`:

```python
def test_post_chat_endpoint_returns_the_payload(session, seeded_corpus, monkeypatch):
    from fastapi.testclient import TestClient

    from app.db.session import get_session
    from app.main import app
    from app.services import chat_service

    plan = {"expanded_query": "How is Sonatype Nexus priced?",
            "steps": [{"tool": "retrieve", "query": "nexus pricing tiers", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "pricing"}]}
    monkeypatch.setattr(chat_service, "_build_plan_model", lambda: _CannedPlan(plan))
    monkeypatch.setattr(chat_service, "_build_draft_model", lambda: _CitesFirstHit())

    app.dependency_overrides[get_session] = lambda: session
    try:
        client = TestClient(app)
        resp = client.post("/chat", json={
            "message": "how is it priced?",
            "history": [{"role": "user", "content": "Tell me about Sonatype Nexus"}],
            "conversation_id": "conv-1",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["grounded"] is True
        assert body["conversation_id"] == "conv-1"
        assert body["plan"]["expanded_query"] == "How is Sonatype Nexus priced?"
        assert len(body["sources"]) == 1
    finally:
        app.dependency_overrides.pop(get_session, None)
```

- [ ] **Step 2: Write the controller**

Create `backend/app/controllers/chat.py`:

```python
from sqlalchemy.orm import Session

from app.services.chat_service import answer_chat


def chat(session: Session, message: str, history: list[dict] | None = None,
         persona: str | None = None, conversation_id: str | None = None) -> dict:
    return answer_chat(session, message, history=history, persona=persona,
                       conversation_id=conversation_id)
```

- [ ] **Step 3: Write the router**

Create `backend/app/routers/chat.py`:

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.controllers import chat as chat_controller
from app.db.session import get_session

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = Field(default_factory=list)
    persona: str | None = None
    conversation_id: str | None = None


@router.post("")
def post_chat(body: ChatRequest, session: Session = Depends(get_session)) -> dict:
    history = [turn.model_dump() for turn in body.history]
    return chat_controller.chat(
        session, body.message, history=history,
        persona=body.persona, conversation_id=body.conversation_id,
    )
```

- [ ] **Step 4: Register the router in `main.py`**

In `backend/app/main.py`, add `chat` to the routers import line and register it next to `ask`. The existing import groups the routers; add `chat` to that import and insert one line after `app.include_router(ask.router)`:

```python
app.include_router(ask.router)
app.include_router(chat.router)
```

(Ensure `chat` is included in the `from app.routers import (...)` block alongside `ask`.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/chat.py backend/app/controllers/chat.py backend/app/main.py tests/test_chat_service.py
git commit -m "feat(chat): expose POST /chat router + controller"
```

---

## Wave 2 gate

- [ ] **Run the chat-service suite and confirm green**

Run: `pytest tests/test_chat_service.py -v`
Expected: PASS (4 tests). On failure, dispatch a Composer fix subagent (≤3 rounds).

---

## Task 6: config/llm.yaml — chat_plan and chat_draft roles

**Files:**
- Modify: `config/llm.yaml`
- Test: covered indirectly; add a config assertion to `tests/test_chat_service.py`.

**Interfaces:**
- Consumes: nothing.
- Produces: two LLM call blocks `chat_plan` and `chat_draft` under `calls`, so `get_model("chat_plan")` / `get_model("chat_draft")` resolve.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chat_service.py`:

```python
def test_chat_llm_roles_are_configured():
    from app.config.loader import load_config

    calls = load_config().llm.calls
    assert "chat_plan" in calls
    assert "chat_draft" in calls
    assert calls["chat_plan"].temperature == 0
    assert calls["chat_draft"].temperature == 0
```

- [ ] **Step 2: Add the roles to `config/llm.yaml`**

Append under `calls:` in `config/llm.yaml` (after the `ask:` block):

```yaml
  # Chat agent — planner. Reads the user turn + recent window and emits a JSON
  # plan (expanded query + ordered retrieve steps). Deterministic, structured.
  chat_plan:
    description: >-
      Plans a chat run: restates the user's question with context resolved and
      emits ordered retrieve steps. Never answers or invents facts.
    model: gpt-5
    temperature: 0
    reasoning_effort: null

  # Chat agent — drafter. Assembles a grounded answer using ONLY retrieved
  # evidence and refuses when the evidence does not support an answer.
  chat_draft:
    description: >-
      Writes a grounded, cited answer strictly from retrieved evidence, or
      refuses. Extractive-only; introduces no unretrieved material.
    model: gpt-5
    temperature: 0
    reasoning_effort: null
```

- [ ] **Step 3: Commit**

```bash
git add config/llm.yaml tests/test_chat_service.py
git commit -m "feat(chat): add chat_plan and chat_draft LLM roles"
```

---

## Task 7: Reimplement /ask on the chat path

**Files:**
- Modify: `backend/app/services/ask_service.py`
- Test: add a legacy-shape test to `tests/test_chat_service.py`

**Interfaces:**
- Consumes: `chat_service.answer_chat` (Task 4).
- Produces: `ask_service.answer_question(session, question, persona=None) -> dict` returning the **existing** `/ask` shape: `{question, persona, grounded, answer, evidence, refusal_reason, nearby_evidence}`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chat_service.py`:

```python
def test_ask_still_answers_in_its_legacy_shape(session, seeded_corpus, monkeypatch):
    from app.services import chat_service
    from app.services.ask_service import answer_question

    plan = {"expanded_query": "How is Sonatype Nexus priced?",
            "steps": [{"tool": "retrieve", "query": "nexus pricing tiers", "preset": "ask_ledger",
                       "filters": {"entity": "sonatype", "signal_type": None}, "reason": "pricing"}]}
    monkeypatch.setattr(chat_service, "_build_plan_model", lambda: _CannedPlan(plan))
    monkeypatch.setattr(chat_service, "_build_draft_model", lambda: _CitesFirstHit())

    out = answer_question(session, "how is sonatype nexus priced?")
    # legacy keys the current /ask consumers rely on
    assert out["grounded"] is True
    assert out["question"] == "how is sonatype nexus priced?"
    assert isinstance(out["evidence"], list) and len(out["evidence"]) == 1
    assert out["refusal_reason"] is None
    assert "nearby_evidence" in out
```

- [ ] **Step 2: Rewrite `ask_service.py` as a thin adapter**

Replace the entire contents of `backend/app/services/ask_service.py` with:

```python
from __future__ import annotations

from sqlalchemy.orm import Session

from agent.log import get_logger, step
from app.services.chat_service import answer_chat

logger = get_logger("app.ask_service")


def answer_question(session: Session, question: str, persona: str | None = None) -> dict:
    """POST /ask, reimplemented on the chat path with no conversation window.

    Maps the chat result back to the legacy /ask response shape so existing
    consumers keep working during the transition.
    """
    step(logger, "ask.request.start", question=question, persona=persona)
    result = answer_chat(session, question, history=[], persona=persona)
    grounded = bool(result.get("grounded"))
    reason = result.get("reason")
    answer = result.get("answer") or (reason or "")
    evidence = result.get("sources", []) if grounded else []
    step(logger, "ask.request.done", question=question, grounded=grounded,
         evidence=len(evidence))
    return {
        "question": question,
        "persona": persona,
        "grounded": grounded,
        "answer": answer,
        "evidence": evidence,
        "refusal_reason": None if grounded else reason,
        "nearby_evidence": result.get("nearby_evidence", []),
    }
```

Note: `ask_service` no longer imports `langgraph`/`agent.graphs.ask`; the boundary test still passes because `answer_chat` lives in `chat_service` which also stays langgraph-free (the graph is built inside it via `agent/`, not imported as langgraph).

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ask_service.py tests/test_chat_service.py
git commit -m "refactor(ask): reimplement POST /ask on the chat path (history=[])"
```

---

## Task 8: Delete the old ask graph

**Files:**
- Delete: `backend/agent/graphs/ask/graph.py`
- Delete: `backend/agent/graphs/ask/state.py`
- Delete: `backend/agent/graphs/ask/__init__.py`
- Modify: `tests/test_ask_graph.py` (remove tests that import the deleted graph; keep the tools-are-read-only assertion)

**Interfaces:**
- Consumes: nothing.
- Produces: no code — removes the superseded single-turn graph. Nothing imports `agent.graphs.ask` after Task 7 (verify with a grep before deleting).

- [ ] **Step 1: Verify nothing imports the old graph**

Run: `rg "agent.graphs.ask" backend tests`
Expected: only matches inside `backend/agent/graphs/ask/` itself and `tests/test_ask_graph.py`. If `ask_service` or anything else still imports it, STOP and fix that first.

- [ ] **Step 2: Trim `tests/test_ask_graph.py`**

The graph-behavior tests (`test_a_supported_question_is_answered_with_citations`, `test_an_unsupported_question_is_refused_not_answered`, `test_the_tool_loop_is_capped`, `test_an_answer_whose_claims_are_not_in_the_hits_is_refused`) exercise the deleted graph. Their grounding coverage now lives in `tests/test_chat_graph.py` and `tests/test_chat_service.py`. Replace the file contents with only the still-valid tool-surface guard:

```python
def test_tools_are_read_only_and_ledger_scoped():
    from agent.tools.ledger import TOOLS

    names = {t.name for t in TOOLS}
    assert names <= {
        "search_signals",
        "get_claim",
        "claim_history",
        "compare_entities",
        "list_sources",
    }
    assert not any("fetch" in n or "write" in n or "delete" in n for n in names)
```

(If `agent.tools.ledger` no longer exists in this branch, delete `tests/test_ask_graph.py` entirely instead — that tool module is unrelated to the chat rebuild.)

- [ ] **Step 3: Delete the old graph files**

```bash
git rm backend/agent/graphs/ask/graph.py backend/agent/graphs/ask/state.py backend/agent/graphs/ask/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_ask_graph.py
git commit -m "chore(ask): delete superseded single-turn ask graph"
```

---

## Wave 3 gate

- [ ] **Run the full backend suite and confirm green**

Run: `pytest -q`
Expected: PASS, including `tests/test_boundaries.py` (proves `app/` still imports no LLM libraries), `tests/test_chat_graph.py`, `tests/test_chat_service.py`, and the trimmed `tests/test_ask_graph.py`. On failure, dispatch a Composer fix subagent (≤3 rounds).

---

## Task 9: Client working-memory window (localStorage, FIFO ≤10)

**Files:**
- Create: `client/src/lib/chatHistory.ts`
- Test: `client/src/lib/chatHistory.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `type ChatTurn = { role: "user" | "assistant"; content: string; citations?: unknown[] }`
  - `MAX_INTERACTIONS = 10`
  - `loadHistory(): ChatTurn[]`
  - `appendExchange(user: ChatTurn, assistant: ChatTurn): ChatTurn[]` — pushes both turns, trims to the last `2 * MAX_INTERACTIONS` turns (10 user↔assistant exchanges), persists, returns the new array.
  - `clearHistory(): void`

- [ ] **Step 1: Write the failing test**

Create `client/src/lib/chatHistory.test.ts`:

```typescript
import { beforeEach, expect, test } from "vitest";
import {
  appendExchange,
  clearHistory,
  loadHistory,
  MAX_INTERACTIONS,
  type ChatTurn,
} from "./chatHistory";

beforeEach(() => {
  clearHistory();
});

test("an appended exchange is persisted and reloads", () => {
  const user: ChatTurn = { role: "user", content: "hello" };
  const assistant: ChatTurn = { role: "assistant", content: "hi", citations: [] };
  appendExchange(user, assistant);
  expect(loadHistory()).toEqual([user, assistant]);
});

test("history keeps only the last 10 interactions, oldest dropped, order preserved", () => {
  for (let i = 0; i < 12; i++) {
    appendExchange(
      { role: "user", content: `q${i}` },
      { role: "assistant", content: `a${i}` },
    );
  }
  const history = loadHistory();
  expect(history.length).toBe(MAX_INTERACTIONS * 2);
  // the two oldest exchanges (q0/a0, q1/a1) were popped
  expect(history[0]).toEqual({ role: "user", content: "q2" });
  expect(history[history.length - 1]).toEqual({ role: "assistant", content: "a11" });
});
```

- [ ] **Step 2: Write `chatHistory.ts`**

Create `client/src/lib/chatHistory.ts`:

```typescript
export type ChatTurn = {
  role: "user" | "assistant";
  content: string;
  citations?: unknown[];
};

export const MAX_INTERACTIONS = 10;
const STORAGE_KEY = "chatHistory";

export function loadHistory(): ChatTurn[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as ChatTurn[]) : [];
  } catch {
    return [];
  }
}

function save(history: ChatTurn[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch {
    /* localStorage unavailable (private mode / quota) — memory is best-effort */
  }
}

export function appendExchange(user: ChatTurn, assistant: ChatTurn): ChatTurn[] {
  const next = [...loadHistory(), user, assistant];
  // FIFO: cap at the last MAX_INTERACTIONS exchanges (2 turns each), dropping oldest.
  const trimmed = next.slice(-MAX_INTERACTIONS * 2);
  save(trimmed);
  return trimmed;
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add client/src/lib/chatHistory.ts client/src/lib/chatHistory.test.ts
git commit -m "feat(client): add localStorage chat history window (FIFO, last 10)"
```

---

## Task 10: Wire the Ask page to POST /chat with the window

**Files:**
- Modify: `client/src/api/endpoints.ts` (add `chatPath`)
- Modify: `client/src/api/types.ts` (add chat types)
- Modify: `client/src/api/client.ts` (add `postChat`)
- Modify: `client/src/pages/Ask.tsx` (use window + `postChat`, persist + re-trim)
- Test: existing `client/src/pages/ask.test.tsx` must still pass (fixture mode); no new assertions required.

**Interfaces:**
- Consumes: `chatHistory` lib (Task 9); `postChat` from `client.ts`.
- Produces:
  - `chatPath(): string` → `"/chat"`.
  - `ChatTurn`, `ChatRequest`, `ChatResponse` in `types.ts`.
  - `api.postChat(body: ChatRequest): Promise<ChatResponse>` — in fixture mode returns the same shape derived from the ask fixture; in live mode POSTs to `/chat`.

- [ ] **Step 1: Add `chatPath` to `endpoints.ts`**

In `client/src/api/endpoints.ts`, after `askPath`:

```typescript
export function chatPath(): string {
  return "/chat";
}
```

- [ ] **Step 2: Add chat types to `types.ts`**

In `client/src/api/types.ts`, near `AskRequest`/`AskResponse`, add:

```typescript
export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  citations?: unknown[];
}

export interface ChatRequest {
  message: string;
  history: ChatTurn[];
  persona?: Persona | null;
  conversation_id?: string | null;
}

export interface ChatResponse {
  conversation_id: string | null;
  answer: string;
  sources: AskEvidence[];
  grounded: boolean;
  plan: {
    expanded_query?: string;
    steps?: {
      tool: string;
      query: string;
      preset: string;
      filters: { entity: string | null; signal_type: string | null };
      reason: string;
    }[];
  };
  reason: string | null;
  nearby_evidence: NearbyItem[];
}
```

- [ ] **Step 3: Add `postChat` to `client.ts`**

In `client/src/api/client.ts`, import the new types (`ChatRequest`, `ChatResponse`) in the `import type { ... }` block, and add a fixture selector plus the method. The fixture derives a `ChatResponse` from the existing ask fixture so `/ask` demo behavior is preserved:

```typescript
function selectChatFixture(body: ChatRequest): ChatResponse {
  const exchange = selectAskFixture({ question: body.message });
  return {
    conversation_id: body.conversation_id ?? null,
    answer: exchange.answer,
    sources: exchange.evidence,
    grounded: exchange.grounded,
    plan: {
      expanded_query: exchange.question,
      steps: [
        {
          tool: "retrieve",
          query: exchange.question,
          preset: "ask_ledger",
          filters: { entity: null, signal_type: null },
          reason: "fixture",
        },
      ],
    },
    reason: exchange.refusal_reason,
    nearby_evidence: exchange.nearby_evidence,
  };
}
```

Then add the method inside the `api` object (next to `postAsk`):

```typescript
  postChat(body: ChatRequest): Promise<ChatResponse> {
    return fixtureOrLive(
      selectChatFixture(body),
      paths.chatPath(),
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  },
```

- [ ] **Step 4: Wire `Ask.tsx` to the window + `postChat`**

In `client/src/pages/Ask.tsx`:

1. Add imports at the top:

```typescript
import { appendExchange, loadHistory } from "../lib/chatHistory";
import type { ChatResponse } from "../api/types";
```

2. Replace the body of `sendQuestion` so it sends the current window and persists both turns. The transcript rendering still uses `AskResponse[]`, so map the `ChatResponse` into an `AskResponse`-shaped exchange:

```typescript
  const sendQuestion = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pending) return;

    setPending(true);
    setPendingQuestion(trimmed);
    setInput("");

    try {
      const history = loadHistory();
      const chat: ChatResponse = await api.postChat({
        message: trimmed,
        history,
      });
      const exchange: AskResponse = {
        question: trimmed,
        grounded: chat.grounded,
        answer: chat.answer,
        evidence: chat.sources,
        refusal_reason: chat.reason,
        nearby_evidence: chat.nearby_evidence,
      };
      setExchanges((prev) => [...prev, exchange]);
      appendExchange(
        { role: "user", content: trimmed },
        {
          role: "assistant",
          content: chat.answer,
          citations: chat.sources.map((s) => s.citation ?? null),
        },
      );
    } finally {
      setPending(false);
      setPendingQuestion(null);
    }
  }, [pending]);
```

(Leave the rest of `Ask.tsx` — suggested questions, transcript, input box — unchanged. The page still renders `AskResponse[]`; only the fetch source and persistence changed.)

- [ ] **Step 5: Commit**

```bash
git add client/src/api/endpoints.ts client/src/api/types.ts client/src/api/client.ts client/src/pages/Ask.tsx
git commit -m "feat(client): send localStorage window to POST /chat from Ask page"
```

---

## Wave 4 gate

- [ ] **Run the client suite and confirm green**

Run (from `client/`): `npm test`
Expected: PASS, including `src/lib/chatHistory.test.ts` (window FIFO) and the existing `src/pages/ask.test.tsx` (citations render, refusal renders, nearby renders) in fixture mode. On failure, dispatch a Composer fix subagent (≤3 rounds).

---

## Task 11: Update project-instruction docs

**Files:**
- Create: `docs/project-instruction/chat.md`
- Modify: `docs/project-instruction/ask.md` (note `/ask` now runs on the chat path)
- Modify: `docs/project-instruction/llm.md` (add `chat_plan`, `chat_draft` rows)

**Interfaces:**
- Consumes: nothing.
- Produces: docs that match the shipped behavior (per the workspace rule that `docs/project-instruction` is the source of truth and must be updated when logic changes).

- [ ] **Step 1: Write `docs/project-instruction/chat.md`**

Create `docs/project-instruction/chat.md`:

```markdown
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
```

- [ ] **Step 2: Update `ask.md` and `llm.md`**

In `docs/project-instruction/ask.md`, add a note at the top that the single-turn
`classify_intent → tool_loop → grounding_gate` graph has been **replaced** by the chat
path (see `chat.md`); `/ask` now calls `chat_service.answer_chat(history=[])`.

In `docs/project-instruction/llm.md`, add two rows to "The calls" table:

```markdown
| `chat_plan` | Chat endpoint — `app/services/chat_service.py` | Emits the JSON run plan (expanded query + ordered retrieve steps). Deterministic. |
| `chat_draft` | Chat endpoint — `app/services/chat_service.py` | Extractive-only grounded answer over retrieved evidence; refuses when unsupported. |
```

- [ ] **Step 3: Commit**

```bash
git add docs/project-instruction/chat.md docs/project-instruction/ask.md docs/project-instruction/llm.md
git commit -m "docs: document the chat graph and /ask reimplementation"
```

---

## Self-Review (completed against the spec)

**1. Spec coverage**

| Spec section | Task |
|---|---|
| §3 module layout (`agent/graphs/chat/`, prompts, `chat_service`, router, controller) | 1, 2, 3, 4, 5 |
| §4 State (`ChatState`, `ChatResult`) | 1 |
| §5 planner (JSON plan, tool/preset validation, entity slug, 1–N steps, expanded_query, temp 0) | 2, 3 (validation), 4 (structured schema), 6 (role) |
| §6 executor (per-step retrieve, slug→ids, dedupe by chunk_id, skip empty-entity, no widening) | 3 |
| §7 drafter (extractive-only, citations⊆hits, empty-answer/outside-citation refuse, empty-hits refuse w/o model, sources from cited, nearby on refusal) | 3, 4 |
| §8 client memory (localStorage, FIFO ≤10, request carries window, response echoes plan) | 9, 10 |
| §9 API/controller (`POST /chat` shape, `/ask` reimplemented) | 5, 7 |
| §10 config (`chat_plan`, `chat_draft`) | 6 |
| §11 testing (planner, executor, drafter grounding ×4, memory window, e2e, corpus verification) | 3, 4, 9 |
| §12 execution protocol (models, test policy, waves) | Global Constraints + Waves |
| §13 definition of done | Wave 3 + Wave 4 gates |
| "delete old ask graph after green" | 8 |
| workspace rule: update `docs/project-instruction` | 11 |

**2. Placeholder scan:** No `TBD`/"handle edge cases"/"similar to Task N"; every code step carries complete code.

**3. Type consistency:** `deps.retrieve(*, query, preset, filters)`, `deps.resolve_entity(slug)`, `deps.plan_model.plan(message, transcript, presets, filter_fields)`, `deps.draft_model.draft(question, hits, persona, transcript)`, `deps.format_sources(hits, citations)`, and `deps.presets`/`deps.filter_fields` are used identically in Task 3's stubs, Task 3's `graph.py`, and Task 4's real `_build_deps`. Hit dicts use `"id"` everywhere. `answer_chat` return keys (`answer, sources, grounded, plan, reason, nearby_evidence, conversation_id`) match the router response, the `/ask` adapter's reads, and the client `ChatResponse` type. `format_evidence` output keys match `AskEvidence` in `types.ts` (`n, quote, source_url, source_name, captured_at, reliability_grade, credibility_score, citation`).
