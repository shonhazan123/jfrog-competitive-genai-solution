from typing import Literal
from pydantic import BaseModel, Field

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

class AppConfig(BaseModel):
    entities: list[EntityConfig]
    sources: list[SourceConfig]
    verification: VerificationConfig
    chunking: ChunkingConfig
