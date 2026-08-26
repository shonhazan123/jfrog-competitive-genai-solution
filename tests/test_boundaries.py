from pathlib import Path

FORBIDDEN = ("langchain", "langgraph", "openai")
APP = Path(__file__).resolve().parents[1] / "backend" / "app"

def test_app_package_never_imports_llm_libraries():
    offenders = []
    for py in APP.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for lib in FORBIDDEN:
            if f"import {lib}" in text or f"from {lib}" in text:
                offenders.append(f"{py.relative_to(APP)} imports {lib}")
    assert offenders == [], (
        "app/ must not import LLM libraries; that belongs in agent/. " + "; ".join(offenders)
    )
