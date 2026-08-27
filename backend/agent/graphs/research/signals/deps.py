from __future__ import annotations

import json

from pydantic import BaseModel

from agent.llm import prompt as load_prompt


class SignalCard(BaseModel):
    usable: bool
    headline: str
    so_what: str
    why_it_matters: str
    tags: list[str]
    source_url: str


class SignalsDeps:
    max_attempts = 3

    def __init__(self, targets, structured_fn, search_fn, gate_model):
        self._targets = targets
        self._structured = structured_fn
        self._search = search_fn
        self._gate = gate_model

    def plan(self):
        return list(self._targets)

    def collect(self, target):
        return self._structured(target)  # None when no structured source exists

    def search(self, target):
        return self._search(target)

    def assess(self, target, material, attempts):
        payload = {
            "competitor": target["name"],
            "aliases": target["aliases"],
            "sub_type": target["sub_type"],
            "material": _as_json(material),
        }
        prompt_text = load_prompt("research_signals") + "\n\nDATA:\n" + json.dumps(payload)
        card: SignalCard = self._gate.invoke(prompt_text)
        if card.usable and card.source_url and card.why_it_matters:
            return "resolved", {
                "competitor": target["competitor"],
                "signal_type": target["signal_type"],
                "headline": card.headline,
                "so_what": card.so_what,
                "why_it_matters": card.why_it_matters,
                "tags": card.tags,
                "source_url": card.source_url,
            }
        return "unresolved", None

    def absent_draft(self, target):
        return {
            "competitor": target["competitor"],
            "sub_type": target["sub_type"],
            "absent": True,
        }


def _as_json(material):
    if material is None:
        return []
    out = []
    for m in material:
        if hasattr(m, "url"):  # SearchHit
            out.append({"title": m.title, "url": m.url, "snippet": m.snippet})
        else:
            out.append(m)
    return out
