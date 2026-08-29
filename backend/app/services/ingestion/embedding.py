import hashlib

from sqlalchemy import func, select

from app.models.delivery import Chunk


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _chunk_field(chunk, name: str, default=None):
    if isinstance(chunk, dict):
        return chunk.get(name, default)
    return getattr(chunk, name, default)


def index_chunks(
    session,
    chunks,
    *,
    record_type: str,
    record_id: int,
    embedder,
    entity_id=None,
    signal_type=None,
    published_at=None,
    reliability_grade=None,
    url=None,
    embed_model="text-embedding-3-small",
    embed_version=1,
) -> int:
    if not chunks:
        return 0

    prepared = []
    for chunk in chunks:
        text = _chunk_field(chunk, "text")
        prefix = _chunk_field(chunk, "prefix")
        prepared.append(
            {
                "chunk": chunk,
                "text": text,
                "prefix": prefix,
                "content_hash": _content_hash(text),
            }
        )

    content_hashes = [item["content_hash"] for item in prepared]
    existing_hashes = set(
        session.scalars(
            select(Chunk.content_hash).where(
                Chunk.record_type == record_type,
                Chunk.record_id == record_id,
                Chunk.content_hash.in_(content_hashes),
                Chunk.embed_model == embed_model,
                Chunk.embed_version == embed_version,
            )
        ).all()
    )

    new_items = [item for item in prepared if item["content_hash"] not in existing_hashes]
    if not new_items:
        return 0

    vectors = embedder.embed([item["text"] for item in new_items])

    for item, vector in zip(new_items, vectors, strict=True):
        chunk = item["chunk"]
        section_path = _chunk_field(chunk, "section_path", [])
        if section_path is not None and not isinstance(section_path, list):
            section_path = list(section_path)

        session.add(
            Chunk(
                record_type=record_type,
                record_id=record_id,
                url=url,
                text=item["text"],
                prefix=item["prefix"],
                section_path=section_path or [],
                token_count=_chunk_field(chunk, "token_count", 0),
                entity_id=entity_id,
                signal_type=signal_type,
                published_at=published_at,
                reliability_grade=reliability_grade,
                content_hash=item["content_hash"],
                embed_model=embed_model,
                embed_version=embed_version,
                embedding=vector,
            )
        )

    session.flush()
    return len(new_items)


def stale_chunk_count(session, current_model: str) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.embed_model != current_model)
        )
        or 0
    )
