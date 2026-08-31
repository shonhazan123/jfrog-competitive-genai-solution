from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class Signal(Base, TimestampMixin):
    __tablename__ = "signal"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"), nullable=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))

    # Derived from extraction. NOT presumed. Most signals are self-assertions,
    # where subject_entity_id == entity_id. Never default this to JFrog.
    subject_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entity.id"), nullable=True)

    signal_type: Mapped[str] = mapped_column(String(32), index=True)
    headline: Mapped[str] = mapped_column(String(256))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    capability_tags: Mapped[list] = mapped_column(JSON, default=list)

    cluster_key: Mapped[str] = mapped_column(String(128), index=True)
    theme_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    corroboration_count: Mapped[int] = mapped_column(Integer, default=1)

    score_sales: Mapped[float] = mapped_column(Float, default=0.0)
    score_product: Mapped[float] = mapped_column(Float, default=0.0)
    score_exec: Mapped[float] = mapped_column(Float, default=0.0)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)

    so_what_sales: Mapped[str | None] = mapped_column(Text, nullable=True)
    so_what_product: Mapped[str | None] = mapped_column(Text, nullable=True)
    so_what_exec: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)

    handling: Mapped[str | None] = mapped_column(String(16), nullable=True)  # caution
    status: Mapped[str] = mapped_column(String(16), default="active")

class SignalEvidence(Base, TimestampMixin):
    __tablename__ = "signal_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signal.id"))
    capture_id: Mapped[int] = mapped_column(ForeignKey("raw_capture.id"))
    quote: Mapped[str] = mapped_column(Text)
    quote_offset: Mapped[int] = mapped_column(Integer)
    match_method: Mapped[str] = mapped_column(String(16))     # synthesis | exact | fuzzy
