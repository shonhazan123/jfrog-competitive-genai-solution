from __future__ import annotations

import json

from pydantic import BaseModel

from agent.graphs.research.grounding import source_url_grounded
from agent.graphs.research.query import broaden_query, dedupe_names
from agent.llm import prompt as load_prompt
from agent.tools.web_search import web_search


class CellVerdict(BaseModel):
    found: bool
    stance: str      # strong | moderate | weak
    summary: str
    source_url: str


class ComparisonDeps:
    max_attempts = 3

    def __init__(self, cells, search_fn=None, gate_model=None):
        self._cells = cells
        self._gate = gate_model
        self._search = search_fn or (
            lambda t, attempt=1: web_search(self._query(t, attempt), k=5)
        )

    def _query(self, target, attempt: int = 1):
        product = " OR ".join(dedupe_names(target["name"], target.get("aliases") or []))
        probes = [
            kw.replace("<rival>", target["name"])
            for kw in target.get("probe_keywords", [])
        ]
        base = f'({product}) {target["label"]} ({" OR ".join(probes)})'
        return broaden_query(base, attempt)

    def plan(self):
        return list(self._cells)

    def collect(self, target):
        return None  # search-first

    def search(self, target, *, attempt: int = 1):
        return self._search(target, attempt=attempt)

    def assess(self, target, hits, attempts):
        payload = {
            "competitor": target["name"],
            "aliases": target["aliases"],
            "dimension": target["label"],
            "jfrog_reference": target["jfrog_reference"],
            "hits": [{"title": h.title, "url": h.url, "snippet": h.snippet} for h in hits],
        }
        prompt_text = load_prompt("research_comparison") + "\n\nDATA:\n" + json.dumps(payload)
        v: CellVerdict = self._gate.invoke(prompt_text)
        if (
            v.found
            and v.source_url
            and v.stance in {"strong", "moderate", "weak"}
            and source_url_grounded(v.source_url, hits)
        ):
            return "resolved", {
                "competitor": target["competitor"],
                "dimension": target["dimension"],
                "stance": v.stance,
                "summary": v.summary,
                "source_url": v.source_url,
            }
        return "unresolved", None

    def absent_draft(self, target):
        return {
            "competitor": target["competitor"],
            "dimension": target["dimension"],
            "stance": "none",
        }
