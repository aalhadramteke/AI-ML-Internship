import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.logging_config import setup_logging
from app.middleware import TimingMiddleware
from app.routers import research, v1, v2
from app.settings import settings

APP_VERSION = "2.1.0"
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    setup_logging(settings.log_level, settings.log_dir)

    app = FastAPI(
        title="Async API Practice",
        description="v1 = synchronous baseline, v2 = async + background tasks, plus a multi-agent research endpoint",
        version=APP_VERSION,
    )

    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    app.add_middleware(TimingMiddleware)

    app.include_router(v1.router)
    app.include_router(v2.router)
    app.include_router(research.router)

    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "version": APP_VERSION, "env": settings.app_env}

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        # Details are logged by TimingMiddleware; never leak them to the client.
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": rid},
            headers={"X-Request-ID": rid} if rid else None,
        )

    logger.info("App created (env=%s, version=%s)", settings.app_env, APP_VERSION)
    return app


app = create_app()
