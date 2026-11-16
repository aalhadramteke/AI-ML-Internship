import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        request_id = str(uuid.uuid4())[:8]
        response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-ms"] = f"{ms:.1f}"
        response.headers["X-Request-ID"] = request_id
        return response