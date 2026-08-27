from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class Claim(Base, TimestampMixin):
    __tablename__ = "claim"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    asserting_entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    claim_text: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(32))
    capability_tags: Mapped[list] = mapped_column(JSON, default=list)
    dimension: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stance: Mapped[str | None] = mapped_column(String(16), nullable=True)  # strong|moderate|weak|none
    status: Mapped[str] = mapped_column(String(16), default="active")
    reliability_grade: Mapped[str] = mapped_column(String(1))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ClaimVersion(Base, TimestampMixin):
    __tablename__ = "claim_version"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"))
    old_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_kind: Mapped[str] = mapped_column(String(16))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"))
    capture_id: Mapped[int] = mapped_column(ForeignKey("raw_capture.id"))
    quote: Mapped[str] = mapped_column(Text)
    quote_offset: Mapped[int] = mapped_column(Integer)
