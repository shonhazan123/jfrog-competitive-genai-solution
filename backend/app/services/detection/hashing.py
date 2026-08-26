import hashlib
from app.services.normalization.clean import normalize_text

def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def normalized_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()
