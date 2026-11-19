import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.schemas import ResearchIn, ResearchOut
from app.security import require_api_key
from app.settings import settings
from research import service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2", tags=["research (agent)"])

_active = 0  # research runs currently in progress (single event-loop thread, so no lock needed)


@router.post("/research", response_model=ResearchOut, dependencies=[Depends(require_api_key)])
async def research(body: ResearchIn):
    """Run the multi-agent pipeline: Coordinator -> Research -> Analyzer -> Critic -> Writer."""
    global _active
    if _active >= settings.max_concurrent_research:
        raise HTTPException(
            status_code=429,
            detail="Research assistant is busy, retry shortly",
            headers={"Retry-After": "30"},
        )
    _active += 1
    try:
        # the graph and LLM calls are blocking, so run them in a worker thread
        return await asyncio.to_thread(service.run_research, body.query)
    except httpx.HTTPError:
        logger.exception("LLM backend unreachable")
        raise HTTPException(status_code=503, detail="LLM backend unavailable") from None
    except Exception:
        logger.exception("Research pipeline failed")
        raise HTTPException(status_code=500, detail="Research pipeline failed") from None
    finally:
        _active -= 1
