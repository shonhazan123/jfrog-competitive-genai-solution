from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class ClaimRef:
    id: int
    claim_text: str
    capability_tags: list[str]

class ClaimLookup(Protocol):
    def candidates(self, subject: str, tags: list[str], k: int = 5) -> list[ClaimRef]: ...
    def jfrog_position(self, capability_tag: str) -> str | None: ...

class EntityRegistry(Protocol):
    def entity_slugs(self) -> list[str]: ...
    def capability_tags(self) -> list[str]: ...
