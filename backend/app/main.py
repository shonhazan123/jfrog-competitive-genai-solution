from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.loader import load_config
from app.routers import (
    activity,
    ask,
    claims,
    comparison,
    config,
    coverage,
    digests,
    email_preview,
    health,
    industry,
    kits,
    runs,
    signals,
    sources,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_config()          # raises ValidationError on bad config, before serving traffic
    yield

app = FastAPI(title="JFrog Competitive Intelligence", lifespan=lifespan)
app.include_router(health.router)
app.include_router(runs.router)
app.include_router(activity.router)
app.include_router(signals.router)
app.include_router(kits.router)
app.include_router(digests.router)
app.include_router(comparison.router)
app.include_router(claims.router)
app.include_router(industry.router)
app.include_router(sources.router)
app.include_router(config.router)
app.include_router(coverage.router)
app.include_router(email_preview.router)
app.include_router(ask.router)
