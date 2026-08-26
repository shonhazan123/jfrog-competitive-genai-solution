import pytest

from agent.graphs.ask.graph import build_ask_graph


class _Hit:
    def __init__(self, id, text):
        self.id = id
        self.text = text


HIT_A = _Hit("hit-a", "Sonatype claims JFrog pricing is premium.")
HIT_B = _Hit("hit-b", "Sonatype positions Nexus as cost-effective vs JFrog.")


@pytest.fixture
def ask_deps():
    def _make(hits=None, always_call_tools=False, model_answer=None):
        hits = hits or []

        class _Model:
            def answer(self, question, hits):
                if model_answer is not None:
                    return {"answer": model_answer, "citations": []}
                return {
                    "answer": " ".join(getattr(h, "text", str(h)) for h in hits),
                    "citations": [getattr(h, "id", h) for h in hits],
                }

        class Deps:
            def __init__(self):
                self.tool_calls = 0
                self.max_tool_calls = 4
                self.always_call_tools = always_call_tools
                self._hits = hits
                self.model = _Model()
                from langgraph.checkpoint.memory import MemorySaver

                self.checkpointer = MemorySaver()

            def retrieve(self, question, filters):
                return list(self._hits)

        return Deps()

    return _make


def test_a_supported_question_is_answered_with_citations(ask_deps):
    graph = build_ask_graph(ask_deps(hits=[HIT_A, HIT_B]))
    result = graph.invoke(
        {"question": "What does Sonatype claim about JFrog pricing?"},
        config={"configurable": {"thread_id": "a1"}},
    )
    assert result["refused"] is False
    assert len(result["citations"]) >= 1


def test_an_unsupported_question_is_refused_not_answered(ask_deps):
    """The refusal is a graph edge, not a prompt instruction."""
    graph = build_ask_graph(ask_deps(hits=[]))
    result = graph.invoke(
        {"question": "What is Sonatype's 2027 revenue forecast?"},
        config={"configurable": {"thread_id": "a2"}},
    )
    assert result["refused"] is True
    assert "grounded evidence" in result["reason"].lower()


def test_the_tool_loop_is_capped(ask_deps):
    deps = ask_deps(hits=[HIT_A], always_call_tools=True)
    graph = build_ask_graph(deps)
    graph.invoke({"question": "loop forever"}, config={"configurable": {"thread_id": "a3"}})
    assert deps.tool_calls <= 4


def test_an_answer_whose_claims_are_not_in_the_hits_is_refused(ask_deps):
    """The grounding gate runs AFTER the loop and before the answer."""
    graph = build_ask_graph(
        ask_deps(hits=[HIT_A], model_answer="JFrog will be acquired in 2027.")
    )
    result = graph.invoke({"question": "any"}, config={"configurable": {"thread_id": "a4"}})
    assert result["refused"] is True


def test_tools_are_read_only_and_ledger_scoped(ask_deps):
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
