import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID and X-Process-Time-ms to every response and logs each request."""

    async def dispatch(self, request, call_next):
        rid = uuid.uuid4().hex[:8]
        request.state.request_id = rid
        start = time.perf_counter()
        logger.info("[%s] --> %s %s", rid, request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("[%s] unhandled error on %s %s", rid, request.method, request.url.path)
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.2f}"
        response.headers["X-Request-ID"] = rid
        logger.info(
            "[%s] <-- %s %s status=%s %.1fms",
            rid, request.method, request.url.path, response.status_code, elapsed_ms,
        )
        return response
