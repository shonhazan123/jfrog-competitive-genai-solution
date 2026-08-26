from urllib.parse import urlparse
from pyrate_limiter import Duration, Limiter, Rate

class DomainRateLimiter:
    """Per-domain politeness limit. Blocks rather than raising when exhausted."""

    def __init__(self, per_minute: int = 20) -> None:
        self._limiter = Limiter(Rate(per_minute, Duration.MINUTE))

    def acquire(self, url: str) -> None:
        self._limiter.try_acquire(urlparse(url).netloc)
