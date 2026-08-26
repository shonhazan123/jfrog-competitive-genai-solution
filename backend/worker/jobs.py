from app.db.session import SessionLocal
from app.models.registry import Source
from app.services.backfill import backfill_source
from app.services.collection.fetcher import Fetcher, StaticFetcher
from app.services.collection.fixture_fetcher import FixtureFetcher
from app.services.collection.robots import RobotsCache
from app.services.seeding import seed
from app.settings import settings

def run_seed() -> None:
    with SessionLocal() as session:
        seed(session)

def run_backfill() -> dict[str, int]:
    """Replay archive history for every enabled snapshot-mode source."""
    totals = {"captures": 0, "claims": 0, "versions": 0}
    use_fixtures = settings.backfill_source == "fixtures"
    fetcher: Fetcher = (
        FixtureFetcher(settings.fixtures_dir) if use_fixtures else StaticFetcher()
    )
    robots = None if use_fixtures else RobotsCache()
    with SessionLocal() as session:
        sources = session.query(Source).filter_by(mode="snapshot", enabled=True).all()
        for source in sources:
            if use_fixtures:
                source.robots_allowed = True
            else:
                source.robots_allowed = robots.allowed(source.url)
            if not source.robots_allowed or source.requires_js:
                continue
            report = backfill_source(session, source, fetcher)
            totals["captures"] += report.captures
            totals["claims"] += report.claims_created
            totals["versions"] += report.versions_created
        session.commit()
    return totals
