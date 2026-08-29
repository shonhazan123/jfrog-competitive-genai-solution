# LLM calls and per-call tuning

Every LLM call the system makes is declared and tuned in [`config/llm.yaml`](../../config/llm.yaml).
There is one block per call so each model can be adjusted independently without
touching code.

## The calls

| Call | Where it runs | Purpose |
|---|---|---|
| `extract` | reserved — no live consumer | Role retained for legacy interpret path removal; no code binds it yet. |
| `contextualize` | reserved — no live consumer | Role retained for legacy interpret path removal; no code binds it yet. |
| `gate` | Industry / Signals / Comparison research graphs | Per-box relevance or usability gate; cheap structured verdict (`gpt-5-mini`, low reasoning). |
| `synthesize` | reserved for richer card synthesis | Optional heavier synthesis pass; not wired in initial agent landing. |
| `ask` | Ask endpoint — `app/services/ask_service.py` | Answers analyst questions strictly from retrieved ledger evidence and refuses when unsupported. Read-only. |
| `chat_plan` | Chat endpoint — `app/services/chat_service.py` | Emits the JSON run plan (expanded query + ordered retrieve steps). Deterministic. `gpt-5-mini`, `reasoning_effort: minimal` (planning is a light structured task; full gpt-5 reasoning cost ~15–45s/turn). |
| `chat_draft` | Chat endpoint — `app/services/chat_service.py` | Extractive-only grounded answer over retrieved evidence; refuses when unsupported. `gpt-5-mini`, `reasoning_effort: low`. Streamed on `/chat/stream` via a TypedDict schema. |

Each call is bound to its output contract by the caller (`.with_structured_output(...)`),
not by config — config only controls the tunable model parameters below.

## Tunable fields

Under `defaults` (applied to every call) or per call under `calls.<name>`:

- `model` — OpenAI model name (only required field).
- `temperature` — sampling temperature; set to `null` to omit it and use the
  model default. Reasoning models such as `gpt-5` only accept their default
  temperature, so use `null` there if you switch models.
- `timeout_seconds` — per-request timeout.
- `max_retries` — automatic retries on transient errors.
- `max_tokens` — cap on generated tokens (`null` = model default).
- `reasoning_effort` — `minimal | low | medium | high` for reasoning models
  (`null` leaves it unset).

A value set on a call always wins over `defaults`, even when set to `null`.

## How it is wired

`config/llm.yaml` → `AppConfig.llm` (validated by `LlmConfig` / `LlmCallConfig`
in `app/config/schema.py`, which merges `defaults` into each call) →
`agent/llm.get_model(role)` builds a `ChatOpenAI` from the call's settings.

`ChatOpenAI` stays in `agent/`; `app/` never imports LLM libraries
(enforced by `tests/test_boundaries.py`).

## Runtime model override

A model name can be overridden without editing config via the `ROLES_<CALL>`
environment variable, e.g. `ROLES_EXTRACT=gpt-5` or `ROLES_ASK=gpt-5-mini`.
Only the model name is overridable this way; all other knobs come from config.

`get_model` is cached per call, and `load_config` is cached per process, so
changes to `config/llm.yaml` take effect on the next process start.

## Embeddings

`agent/llm.get_embedder()` returns an object with `.embed(list[str]) -> list[list[float]]`,
matching `index_chunks`' contract. Used by `app/services/research/provenance.index_finding`.
The OpenAI client is created lazily on first embed (so import/get_embedder works without
`OPENAI_API_KEY`; live indexing still needs credentials).
