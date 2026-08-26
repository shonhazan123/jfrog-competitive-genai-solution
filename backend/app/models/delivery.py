from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserVisit(Base, TimestampMixin):
    __tablename__ = "user_visit"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(128))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DigestRun(Base, TimestampMixin):
    __tablename__ = "digest_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    persona: Mapped[str] = mapped_column(String(16))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    item_count: Mapped[int] = mapped_column(Integer, default=0)


class Delivery(Base, TimestampMixin):
    __tablename__ = "delivery"
    id: Mapped[int] = mapped_column(primary_key=True)
    digest_run_id: Mapped[int] = mapped_column(ForeignKey("digest_run.id"))
    recipient: Mapped[str] = mapped_column(String(256))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16))


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunk"
    id: Mapped[int] = mapped_column(primary_key=True)
    record_type: Mapped[str] = mapped_column(String(32))
    record_id: Mapped[int] = mapped_column(Integer)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_path: Mapped[list] = mapped_column(JSON, default=list)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signal_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reliability_grade: Mapped[str | None] = mapped_column(String(1), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    embed_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embed_version: Mapped[int] = mapped_column(Integer, default=1)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(prefix,'') || ' ' || text)", persisted=True),
        nullable=True,
    )
