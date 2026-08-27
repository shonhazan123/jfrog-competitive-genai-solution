import os
from functools import lru_cache
from pathlib import Path
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from app.config.loader import load_config
from agent.log import get_logger, step

PROMPTS = Path(__file__).parent / "prompts"
logger = get_logger("agent.llm")


def _call_config(role: str):
    """Look up the tunable settings for a named LLM call from config/llm.yaml."""
    calls = load_config().llm.calls
    if role not in calls:
        raise KeyError(
            f"Unknown LLM call {role!r}. Configured calls: {sorted(calls)}. "
            "Add a block for it under `calls` in config/llm.yaml."
        )
    return calls[role]


@lru_cache(maxsize=8)
def get_model(role: str) -> ChatOpenAI:
    """Build the ChatOpenAI client for a named LLM call from config/llm.yaml.

    Every knob (model, temperature, timeout, retries, token cap, reasoning
    effort) is set per call in config so each can be tuned independently. The
    model name can still be overridden at runtime with ROLES_<CALL> (e.g.
    ROLES_EXTRACT=gpt-5). No tools are ever bound to the extract model: it reads
    untrusted scraped content and must emit nothing but a fixed schema.
    """
    cfg = _call_config(role)
    kwargs: dict = {
        "model": os.environ.get(f"ROLES_{role.upper()}", cfg.model),
        "timeout": cfg.timeout_seconds,
        "max_retries": cfg.max_retries,
    }
    # Reasoning models (gpt-5, o-series) reject a non-default temperature, so a
    # null temperature means "leave it unset and use the model default".
    if cfg.temperature is not None:
        kwargs["temperature"] = cfg.temperature
    if cfg.max_tokens is not None:
        kwargs["max_tokens"] = cfg.max_tokens
    if cfg.reasoning_effort is not None:
        kwargs["reasoning_effort"] = cfg.reasoning_effort
    model_name = kwargs["model"]
    step(
        logger,
        "llm.model",
        role=role,
        model=model_name,
        temperature=cfg.temperature,
        timeout_seconds=cfg.timeout_seconds,
        max_retries=cfg.max_retries,
        reasoning_effort=cfg.reasoning_effort,
    )
    return ChatOpenAI(**kwargs)

@lru_cache(maxsize=16)
def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def get_checkpointer():
    """In-memory checkpointer for the interpret graph. Lives in agent/ so app/ never imports langgraph."""
    return MemorySaver()
