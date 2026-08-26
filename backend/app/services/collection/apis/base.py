from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from app.models.registry import Source
from app.services.collection.fetcher import Fetcher

@dataclass(frozen=True)
class ApiRecord:
    external_id: str
    title: str
    body: str
    occurred_at: datetime | None
    url: str
    signal_type_hint: str | None = None
    extra: dict = field(default_factory=dict)

class ApiAdapter(Protocol):
    key: str
    def collect(self, source: Source, fetcher: Fetcher) -> list[ApiRecord]: ...
