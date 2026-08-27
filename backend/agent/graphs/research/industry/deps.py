from __future__ import annotations

import json

from pydantic import BaseModel

from agent.llm import prompt as load_prompt
from agent.tools.web_search import SearchHit, web_search


class IndustryItem(BaseModel):
    headline: str
    body: str
    why_it_matters: str
    source_url: str


class IndustryAssessment(BaseModel):
    kept: list[IndustryItem]


class IndustryDeps:
    max_attempts = 3

    def __init__(self, buckets, gate_model, search=None):
        self._buckets = buckets
        self._gate = gate_model
        self._search = search or (lambda target: web_search(self._query(target), k=6))

    def _query(self, target: dict) -> str:
        return f'{target["label"]} ({" OR ".join(target["include"])})'

    def plan(self) -> list[dict]:
        return list(self._buckets)

    def collect(self, target: dict):
        return None  # search-first

    def search(self, target: dict):
        return self._search(target)

    def assess(self, target: dict, hits, attempts: int):
        payload = {
            "bucket": target["key"], "include": target["include"], "exclude": target["exclude"],
            "hits": [{"title": h.title, "url": h.url, "snippet": h.snippet} for h in hits],
        }
        prompt_text = load_prompt("research_industry") + "\n\nDATA:\n" + json.dumps(payload)
        result: IndustryAssessment = self._gate.invoke(prompt_text)
        kept = [i for i in result.kept if i.source_url]
        if kept:
            return "resolved", {
                "bucket": target["key"], "signal_type": target["signal_type"],
                "items": [i.model_dump() for i in kept],
            }
        return "unresolved", None

    def absent_draft(self, target: dict):
        return {"bucket": target["key"], "signal_type": target["signal_type"], "items": []}
