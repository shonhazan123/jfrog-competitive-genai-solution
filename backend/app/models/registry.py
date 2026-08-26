from sqlalchemy import Boolean, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin

class Entity(Base, TimestampMixin):
    __tablename__ = "entity"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16))
    tier: Mapped[int] = mapped_column(Integer)
    aliases: Mapped[list] = mapped_column(JSON, default=list)

class Source(Base, TimestampMixin):
    __tablename__ = "source"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    url: Mapped[str] = mapped_column(String(1024))
    kind: Mapped[str] = mapped_column(String(16))
    mode: Mapped[str] = mapped_column(String(16))
    reliability_grade: Mapped[str] = mapped_column(String(1))
    is_primary: Mapped[bool] = mapped_column(Boolean)
    check_frequency_minutes: Mapped[int] = mapped_column(Integer)
    requires_js: Mapped[bool] = mapped_column(Boolean, default=False)
    row_selector: Mapped[str | None] = mapped_column(String(256), nullable=True)
    adapter: Mapped[str | None] = mapped_column(String(32), nullable=True)
    robots_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(256), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
