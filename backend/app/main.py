import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import monitoring
from app.api.routes import health, incidents, integrations, metrics
from app.core.config import settings
from app.workers.monitor import monitor_forever


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = None
    if settings.monitoring_enabled:
        task = asyncio.create_task(
            monitor_forever(
                monitoring,
                settings.monitoring_interval_seconds,
            )
        )
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="OpsPilot AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(incidents.router)
app.include_router(integrations.router)
