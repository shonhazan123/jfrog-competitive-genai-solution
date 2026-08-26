import html
import re
import unicodedata

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff\u00ad"), None)
_SMART_QUOTES = {
    ord("\u201c"): '"', ord("\u201d"): '"',
    ord("\u2018"): "'", ord("\u2019"): "'",
}
_WHITESPACE = re.compile(r"\s+")

def normalize_text(s: str) -> str:
    s = html.unescape(s)
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_ZERO_WIDTH)
    s = s.translate(_SMART_QUOTES)
    s = s.replace("\u00a0", " ")
    return _WHITESPACE.sub(" ", s).strip().lower()
