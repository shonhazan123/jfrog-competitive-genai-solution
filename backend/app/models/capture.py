from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class RawCapture(Base, TimestampMixin):
    """Append-only. No code path may update or delete a row of this table."""
    __tablename__ = "raw_capture"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    blob_path: Mapped[str] = mapped_column(String(512))
    extracted_text: Mapped[str] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(String(16), default="live")

class Document(Base, TimestampMixin):
    __tablename__ = "document"
    id: Mapped[int] = mapped_column(primary_key=True)
    capture_id: Mapped[int] = mapped_column(ForeignKey("raw_capture.id"))
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    canonical_url: Mapped[str] = mapped_column(String(1024))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clean_text: Mapped[str] = mapped_column(Text)

class PageSnapshot(Base, TimestampMixin):
    __tablename__ = "page_snapshot"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"))
    capture_id: Mapped[int] = mapped_column(ForeignKey("raw_capture.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    text_hash: Mapped[str] = mapped_column(String(64))
    rows: Mapped[list] = mapped_column(JSON)
