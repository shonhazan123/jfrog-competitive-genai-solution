from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.loader import load_config
from app.logging_config import setup_logging
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
    setup_logging()
    load_config()          # raises ValidationError on bad config, before serving traffic
    yield

app = FastAPI(title="JFrog Competitive Intelligence", lifespan=lifespan)

# The React client is served from a different origin (localhost:5173) than the
# API (localhost:8000), so the browser sends a CORS preflight before each call.
# Without this the browser blocks every request with a CORS error. Any localhost
# / 127.0.0.1 port is allowed so the dev client works regardless of its port.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

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
