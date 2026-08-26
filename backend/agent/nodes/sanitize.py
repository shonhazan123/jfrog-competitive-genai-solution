import re
import nh3

HIDDEN = re.compile(
    r"<[^>]+style=[\"'][^\"']*(display\s*:\s*none|visibility\s*:\s*hidden)[^\"']*[\"'][^>]*>.*?</[^>]+>",
    re.IGNORECASE | re.DOTALL,
)

def sanitize(state, deps):
    raw = state["raw_text"]
    without_hidden = HIDDEN.sub(" ", raw)
    stripped = nh3.clean(without_hidden, tags=set())
    text = " ".join(stripped.split())[: deps.max_input_chars]
    return {
        "sanitized_text": text,
        "trace": state.get("trace", []) + [{"node": "sanitize", "chars": len(text)}],
    }
