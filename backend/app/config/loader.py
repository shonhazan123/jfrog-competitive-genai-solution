from functools import lru_cache
from pathlib import Path
import yaml
from app.config.schema import AppConfig
from app.settings import settings

def _read(name: str) -> dict:
    return yaml.safe_load((Path(settings.config_dir) / name).read_text(encoding="utf-8"))

@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    return AppConfig(
        entities=_read("entities.yaml")["entities"],
        sources=_read("sources.yaml")["sources"],
        verification=_read("verification.yaml"),
        chunking=_read("chunking.yaml"),
        signal_types=_read("signal_types.yaml"),
        routing=_read("routing.yaml"),
        materiality=_read("materiality.yaml"),
        watchlist=_read("watchlist.yaml"),
        jfrog_positions=_read("jfrog_positions.yaml"),
        trends=_read("trends.yaml"),
        delivery=_read("delivery.yaml"),
        retrieval=_read("retrieval.yaml"),
    )
