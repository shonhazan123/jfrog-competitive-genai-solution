from typing import Literal
from pydantic import BaseModel, Field, field_validator

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
    mode: Literal["feed", "snapshot"]
    reliability_grade: Literal["A", "B", "C", "D", "E", "F"]
    is_primary: bool
    check_frequency_minutes: int = Field(ge=5)
    requires_js: bool = False
    row_selector: str | None = None

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

class WatchlistConfig(BaseModel):
    terms: list[str]

class AppConfig(BaseModel):
    entities: list[EntityConfig]
    sources: list[SourceConfig]
    verification: VerificationConfig
    chunking: ChunkingConfig
    signal_types: SignalTypesConfig
    routing: RoutingConfig
    materiality: MaterialityConfig
    watchlist: WatchlistConfig
