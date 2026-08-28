from __future__ import annotations

from typing import Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from agent.log import get_logger, step

logger = get_logger("agent.research")


class ResearchState(TypedDict):
    targets: list[dict]
    cursor: int
    attempts: int
    drafts: list[dict]
    max_attempts: int


class ResearchDeps(Protocol):
    max_attempts: int
    def plan(self) -> list[dict]: ...
    def collect(self, target: dict) -> object | None: ...
    def search(self, target: dict) -> object: ...
    def assess(self, target: dict, material: object, attempts: int) -> tuple[str, dict | None]: ...
    def absent_draft(self, target: dict) -> dict: ...


def build_research_graph(deps: ResearchDeps):
    def plan_node(state: ResearchState) -> dict:
        targets = deps.plan()
        step(logger, "research.plan", targets=len(targets))
        return {"targets": targets, "cursor": 0, "attempts": 0, "drafts": []}

    def resolve_node(state: ResearchState) -> dict:
        """Resolve targets[cursor] to a draft (resolved) or an absent draft,
        looping to search on 'unresolved' up to max_attempts. Bounded, so it
        cannot spin — the whole per-target loop lives in this one node."""
        target = state["targets"][state["cursor"]]
        drafts = list(state["drafts"])
        material = deps.collect(target)
        attempts = 0
        if material is None:  # search-first surfaces
            material = deps.search(target)
            attempts = 1
        while True:
            verdict, draft = deps.assess(target, material, attempts)
            if verdict == "resolved" and draft is not None:
                drafts.append(draft)
                break
            if verdict == "absent" or attempts >= state["max_attempts"]:
                drafts.append(deps.absent_draft(target))
                break
            if isinstance(material, list) and len(material) == 0:
                drafts.append(deps.absent_draft(target))
                break
            material = deps.search(target)  # unresolved -> fall back and retry
            attempts += 1
        return {"drafts": drafts, "cursor": state["cursor"] + 1, "attempts": 0}

    def _more(state: ResearchState) -> str:
        return "resolve" if state["cursor"] < len(state["targets"]) else "done"

    builder = StateGraph(ResearchState)
    builder.add_node("plan", plan_node)
    builder.add_node("resolve", resolve_node)
    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", _more, {"resolve": "resolve", "done": END})
    builder.add_conditional_edges("resolve", _more, {"resolve": "resolve", "done": END})
    return builder.compile()


def run_research(deps: ResearchDeps) -> list[dict]:
    graph = build_research_graph(deps)
    final = graph.invoke(
        {"targets": [], "cursor": 0, "attempts": 0, "drafts": [], "max_attempts": deps.max_attempts},
        config={"recursion_limit": 1000},
    )
    return final["drafts"]
