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
