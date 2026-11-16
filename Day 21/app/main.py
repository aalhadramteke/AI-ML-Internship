from fastapi import FastAPI
from app.middleware import TimingMiddleware
from app.routers import v1, v2

app = FastAPI(
    title="Async API Practice",
    version="2.0.0",
    description="v1 = synchronous baseline, v2 = async + background tasks",
)
app.add_middleware(TimingMiddleware)

app.include_router(v1.router, prefix="/api/v1", tags=["v1 (sync)"])
app.include_router(v2.router, prefix="/api/v2", tags=["v2 (async)"])