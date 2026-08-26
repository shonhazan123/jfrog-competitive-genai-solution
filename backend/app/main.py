from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import health, runs
from app.config.loader import load_config

@asynccontextmanager
async def lifespan(_: FastAPI):
    load_config()          # raises ValidationError on bad config, before serving traffic
    yield

app = FastAPI(title="JFrog Competitive Intelligence", lifespan=lifespan)
app.include_router(health.router)
app.include_router(runs.router)
