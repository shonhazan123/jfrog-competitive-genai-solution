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
