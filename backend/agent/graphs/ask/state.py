from dataclasses import dataclass
from typing import TypedDict


@dataclass
class AskResult:
    answer: str
    citations: list
    refused: bool
    reason: str


class AskState(TypedDict, total=False):
    question: str
    filters: dict
    answer: str
    citations: list
    refused: bool
    reason: str
    tool_iterations: int
