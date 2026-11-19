import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.settings import settings


async def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """If API_KEY is configured, require a matching X-API-Key header."""
    expected = settings.api_key
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
