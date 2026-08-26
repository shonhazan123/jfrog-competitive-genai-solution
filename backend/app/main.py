from fastapi import FastAPI
from app.routers import health

app = FastAPI(title="JFrog Competitive Intelligence")
app.include_router(health.router)
