import re
from dataclasses import dataclass

import tiktoken

from app.config.schema import ChunkingConfig
from app.services.normalization.elements import Element, ElementKind

_ENCODING = tiktoken.get_encoding("cl100k_base")


@dataclass(frozen=True)
class Chunk:
    text: str
    prefix: str
    section_path: tuple[str, ...]
    element_orders: tuple[int, ...]
    token_count: int


def _count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _is_heading_break(element: Element, cfg: ChunkingConfig) -> bool:
    return (
        element.kind == ElementKind.heading
        and element.level is not None
        and element.level <= cfg.break_on_heading_level
    )


def _make_prefix(section_path: tuple[str, ...]) -> str:
    return f"[{' · '.join(section_path)}]"


def _build_chunk(elements: list[Element]) -> Chunk:
    text = "\n".join(el.text for el in elements)
    section_path = elements[0].path
    return Chunk(
        text=text,
        prefix=_make_prefix(section_path),
        section_path=section_path,
        element_orders=tuple(el.order for el in elements),
        token_count=sum(_count_tokens(el.text) for el in elements),
    )


def _split_by_chars(text: str, max_tokens: int) -> list[str]:
    if _count_tokens(text) <= max_tokens:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = len(text)
        while end > start and _count_tokens(text[start:end]) > max_tokens:
            end -= 1
        if end == start:
            end = start + 1
        parts.append(text[start:end])
        start = end
    return parts


def _split_paragraph_text(text: str, max_tokens: int) -> list[str]:
    if _count_tokens(text) <= max_tokens:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) > 1:
        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if _count_tokens(candidate) <= max_tokens:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                if _count_tokens(sentence) > max_tokens:
                    chunks.extend(_split_by_chars(sentence, max_tokens))
                    current = ""
                else:
                    current = sentence
        if current:
            chunks.append(current)
        return chunks
    return _split_by_chars(text, max_tokens)


def chunk_elements(elements: list[Element], cfg: ChunkingConfig) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_group: list[Element] = []

    def flush() -> None:
        nonlocal current_group
        if current_group:
            chunks.append(_build_chunk(current_group))
            current_group = []

    for element in elements:
        if _is_heading_break(element) and current_group:
            flush()

        if element.kind.value in cfg.never_split:
            element_tokens = _count_tokens(element.text)
            if element_tokens > cfg.target_tokens:
                flush()
                chunks.append(_build_chunk([element]))
                continue

        if (
            element.kind == ElementKind.paragraph
            and _count_tokens(element.text) > cfg.max_tokens
        ):
            flush()
            for part in _split_paragraph_text(element.text, cfg.max_tokens):
                chunks.append(
                    Chunk(
                        text=part,
                        prefix=_make_prefix(element.path),
                        section_path=element.path,
                        element_orders=(element.order,),
                        token_count=_count_tokens(part),
                    )
                )
            continue

        if current_group:
            group_tokens = sum(_count_tokens(el.text) for el in current_group)
            if group_tokens + _count_tokens(element.text) > cfg.target_tokens:
                flush()
                current_group = [element]
            else:
                current_group.append(element)
        else:
            current_group = [element]

    flush()
    return chunks
