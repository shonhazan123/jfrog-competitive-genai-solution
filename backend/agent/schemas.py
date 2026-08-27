from datetime import date
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, create_model

class SignalType(StrEnum):
    product_capability = "product_capability"
    positioning_messaging = "positioning_messaging"
    pricing_packaging = "pricing_packaging"
    security_trust = "security_trust"
    corporate_financial = "corporate_financial"
    partnership_ecosystem = "partnership_ecosystem"
    customer_evidence = "customer_evidence"
    market_regulatory = "market_regulatory"
    talent_org = "talent_org"

class Contextualisation(BaseModel):
    so_what_sales: str = Field(max_length=600)
    so_what_product: str = Field(max_length=600)
    so_what_exec: str = Field(max_length=600)
    why_it_matters: str = Field(max_length=140)
    relevance_adjustment: float = Field(ge=-1.0, le=1.0, default=0.0)
    adjustment_reason: str = ""

def build_extraction_model(entities: list[str], capability_tags: list[str]):
    """Closed enums built from live config, so the model cannot emit an entity or
    capability that the team has not configured. Rebuilt on config_version change."""
    entity_enum = Literal[tuple(entities)]          # type: ignore[valid-type]
    tag_enum = Literal[tuple(capability_tags)]      # type: ignore[valid-type]

    claim = create_model(
        "ClaimCandidate",
        claim_text=(str, Field(max_length=400)),
        quote=(str, Field(min_length=1, max_length=600)),   # required — no unsourced claims
        claim_type=(Literal["capability", "pricing", "positioning", "security"], ...),
        capability_tags=(list[tag_enum], Field(default_factory=list)),
    )
    return create_model(
        "Extraction",
        signal_type=(SignalType, ...),
        subject_entity=(entity_enum | None, None),
        asserting_entity=(entity_enum, ...),
        mentions_jfrog=(bool, False),
        occurred_at=(date | None, None),
        headline=(str, Field(max_length=90)),
        claims=(list[claim], Field(default_factory=list)),
    )
