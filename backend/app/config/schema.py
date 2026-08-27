from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

class EntityConfig(BaseModel):
    slug: str
    name: str
    kind: Literal["competitor", "self", "industry"]
    tier: int = Field(ge=1, le=3)
    aliases: list[str] = []

class SourceConfig(BaseModel):
    key: str
    entity: str
    url: str
    kind: Literal["atom", "rss", "html_page", "api", "sitemap"]
    mode: Literal["feed", "snapshot", "api"]
    reliability_grade: Literal["A", "B", "C", "D", "E", "F"]
    is_primary: bool
    check_frequency_minutes: int = Field(ge=5)
    requires_js: bool = False
    row_selector: str | None = None
    adapter: str | None = None
    covers: list[str] = Field(default_factory=list)

class FuzzyConfig(BaseModel):
    enabled: bool = True
    accept_threshold: int = Field(ge=0, le=100)
    min_quote_chars: int = Field(ge=1)

class QuoteMatchingConfig(BaseModel):
    fuzzy: FuzzyConfig

class VerificationConfig(BaseModel):
    quote_matching: QuoteMatchingConfig

class ChunkingConfig(BaseModel):
    target_tokens: int = Field(ge=100)
    max_tokens: int = Field(ge=100)
    break_on_heading_level: int = Field(ge=1, le=6)
    never_split: list[str]

class SignalTypesConfig(BaseModel):
    types: list[str]
    capability_tags: list[str]
    coverage_columns: list[str]

class RoutingConfig(BaseModel):
    matrix: dict[str, dict[str, int]]

    @field_validator("matrix")
    @classmethod
    def relevance_in_range(cls, v):
        for signal_type, row in v.items():
            for persona, value in row.items():
                if not 0 <= value <= 3:
                    raise ValueError(f"{signal_type}.{persona}={value} outside 0..3")
        return v

class InterruptConfig(BaseModel):
    cross_assertion_about_jfrog: bool
    security_cvss_at_least: float
    corporate_subtypes: list[str]

class CandidateConfig(BaseModel):
    min_candidate_chars: int = Field(ge=1)
    max_candidates_per_document: int = Field(ge=1)

class ClusterConfig(BaseModel):
    window_days: int = Field(ge=1)
    title_similarity: int = Field(ge=0, le=100)

class MaterialityConfig(BaseModel):
    base_multiplier: float
    modifiers: dict
    recency_halflife_days: int = Field(ge=1)
    llm_adjustment_range: tuple[float, float]
    threshold: dict[str, float]
    budget: dict[str, int]
    max_per_entity: int = Field(ge=1)
    interrupt: InterruptConfig
    candidates: CandidateConfig
    cluster: ClusterConfig
    tiers: dict[str, float]

class WatchlistConfig(BaseModel):
    terms: list[str]

class JfrogPosition(BaseModel):
    dimension: str
    origin: Literal["authored"]
    text: str

class JfrogPositionsConfig(BaseModel):
    positions: list[JfrogPosition]

class TrendConfig(BaseModel):
    window_weeks: int
    comparison_windows: int
    min_signals_for_trend: int
    direction: dict[str, float]
    velocity: dict[str, float]
    confidence: dict[str, dict[str, int]]

class DeliveryConfig(BaseModel):
    smtp: dict
    send_at: dict[str, str]
    recipients: dict[str, list[str]]
    app_base_url: str

class RetrievalConfig(BaseModel):
    rrf_k: int
    candidate_pool: int
    max_per_document: int
    hnsw_ef_search: int
    rerank: dict
    presets: dict[str, dict]

class KitIncludes(BaseModel):
    signal_types: list[str]

class KitDef(BaseModel):
    key: str
    label: str
    question: str
    category: str
    order: int
    includes: KitIncludes

class KitsConfig(BaseModel):
    kits: list[KitDef]
    promote_to_deal_threats_when: dict[str, str]

class PriorityBand(BaseModel):
    max: int = Field(ge=0, le=100)
    label: str

class LabelsConfig(BaseModel):
    signal_types: dict[str, str]
    tiers: dict[str, str]
    states: dict[str, str]
    personas: dict[str, str]
    origins: dict[str, str]

ReasoningEffort = Literal["minimal", "low", "medium", "high"]


class LlmDefaults(BaseModel):
    """Fallback settings applied to every LLM call that does not override them."""

    provider: Literal["openai"] = "openai"
    temperature: float | None = 0.0
    timeout_seconds: float = Field(default=60, gt=0)
    max_retries: int = Field(default=2, ge=0)
    max_tokens: int | None = Field(default=None, ge=1)
    reasoning_effort: ReasoningEffort | None = None


class LlmCallConfig(BaseModel):
    """Tunable settings for a single named LLM call (see config/llm.yaml)."""

    description: str = ""
    provider: Literal["openai"] = "openai"
    model: str
    temperature: float | None = 0.0
    timeout_seconds: float = Field(default=60, gt=0)
    max_retries: int = Field(default=2, ge=0)
    max_tokens: int | None = Field(default=None, ge=1)
    reasoning_effort: ReasoningEffort | None = None


class LlmConfig(BaseModel):
    defaults: LlmDefaults = Field(default_factory=LlmDefaults)
    calls: dict[str, LlmCallConfig]

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, data):
        # Merge `defaults` into each call so a call only needs to specify what it
        # overrides. An explicit value on a call (even null) always wins.
        if not isinstance(data, dict):
            return data
        defaults = dict(data.get("defaults") or {})
        calls = data.get("calls") or {}
        merged: dict[str, dict] = {}
        for name, call in calls.items():
            call = dict(call or {})
            for key, value in defaults.items():
                call.setdefault(key, value)
            merged[name] = call
        return {"defaults": defaults, "calls": merged}


class AppConfig(BaseModel):
    entities: list[EntityConfig]
    sources: list[SourceConfig]
    verification: VerificationConfig
    chunking: ChunkingConfig
    signal_types: SignalTypesConfig
    routing: RoutingConfig
    materiality: MaterialityConfig
    watchlist: WatchlistConfig
    jfrog_positions: JfrogPositionsConfig
    trends: TrendConfig
    delivery: DeliveryConfig
    retrieval: RetrievalConfig
    kits: KitsConfig
    labels: LabelsConfig
    llm: LlmConfig
