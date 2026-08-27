import re
import nh3

from agent.log import get_logger, step

HIDDEN = re.compile(
    r"<[^>]+style=[\"'][^\"']*(display\s*:\s*none|visibility\s*:\s*hidden)[^\"']*[\"'][^>]*>.*?</[^>]+>",
    re.IGNORECASE | re.DOTALL,
)

logger = get_logger("agent.sanitize")


def sanitize(state, deps):
    capture_id = state.get("capture_id")
    raw_len = len(state["raw_text"])
    step(logger, "sanitize.start", capture_id=capture_id, raw_chars=raw_len)
    raw = state["raw_text"]
    without_hidden = HIDDEN.sub(" ", raw)
    stripped = nh3.clean(without_hidden, tags=set())
    text = " ".join(stripped.split())[: deps.max_input_chars]
    step(logger, "sanitize.done", capture_id=capture_id, sanitized_chars=len(text))
    return {
        "sanitized_text": text,
        "trace": state.get("trace", []) + [{"node": "sanitize", "chars": len(text)}],
    }
