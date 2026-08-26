from typing import Literal, TypedDict

class InterpretState(TypedDict, total=False):
    capture_id: int
    source_meta: dict
    raw_text: str
    change_context: dict | None
    sanitized_text: str
    extraction: dict | None
    verification: dict | None
    repair_attempts: int
    _max_repairs: int
    candidates: list[dict]
    relations: list[dict]
    contextualization: dict | None
    status: Literal["ok", "quarantined", "rejected"]
    errors: list[str]
    trace: list[dict]
