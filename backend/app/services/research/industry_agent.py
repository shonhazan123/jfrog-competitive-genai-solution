from pathlib import Path

import yaml

from app.settings import settings


def load_buckets() -> list[dict]:
    data = yaml.safe_load(
        (Path(settings.config_dir) / "industry_buckets.yaml").read_text(encoding="utf-8")
    )
    return data["buckets"]
