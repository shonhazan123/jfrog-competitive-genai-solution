from dataclasses import dataclass, field
from enum import StrEnum

class ElementKind(StrEnum):
    heading = "heading"
    paragraph = "paragraph"
    list_item = "list_item"
    table_row = "table_row"
    code_block = "code_block"
    quote = "quote"
    caption = "caption"

@dataclass(frozen=True)
class Element:
    kind: ElementKind
    text: str
    order: int
    level: int | None = None
    path: tuple[str, ...] = ()
    attrs: dict = field(default_factory=dict)
