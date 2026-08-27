from pathlib import Path

import yaml

from app.settings import settings


def load_competitors() -> list[dict]:
    cfg_dir = Path(settings.config_dir)
    allow = yaml.safe_load((cfg_dir / "competitors.yaml").read_text(encoding="utf-8"))["competitors"]
    entities = yaml.safe_load((cfg_dir / "entities.yaml").read_text(encoding="utf-8"))["entities"]
    by_slug = {e["slug"]: e for e in entities}
    return [{"slug": s, "name": by_slug[s]["name"], "aliases": by_slug[s].get("aliases", [])} for s in allow]
