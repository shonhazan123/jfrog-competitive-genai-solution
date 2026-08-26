import os
from functools import lru_cache
from pathlib import Path
from langchain_openai import ChatOpenAI

PROMPTS = Path(__file__).parent / "prompts"
_DEFAULT_ROLES = {"extract": "gpt-5-mini", "contextualize": "gpt-5"}


def _load_roles() -> dict[str, str]:
    roles = dict(_DEFAULT_ROLES)
    for role in roles:
        override = os.environ.get(f"ROLES_{role.upper()}")
        if override:
            roles[role] = override
    return roles


ROLES = _load_roles()  # override individual roles via ROLES_EXTRACT / ROLES_CONTEXTUALIZE

@lru_cache(maxsize=8)
def get_model(role: str) -> ChatOpenAI:
    """No tools are ever bound to the extract model. It reads untrusted scraped
    content and must be able to emit nothing but a fixed schema."""
    return ChatOpenAI(model=ROLES[role], temperature=0, timeout=60, max_retries=2)

@lru_cache(maxsize=16)
def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
