import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends

from app.deps import Database, get_db
from app.schemas import OrderIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2", tags=["v2 (async)"])


async def _send_email_safely(db: Database, order: OrderIn) -> None:
    """Background task: a failing email must be logged, never crash silently."""
    try:
        await db.asend_email(order)
    except Exception:
        logger.exception("Background email failed for order item=%s", order.item)


@router.get("/report/{item_id}")
async def report(item_id: int, db: Database = Depends(get_db)):
    item, external = await asyncio.gather(          # both calls overlap
        db.afetch_item(item_id), db.acall_external(item_id)
    )
    return {"version": "v2", "item": item, "external": external}


@router.post("/orders", status_code=201)
async def create_order(order: OrderIn, background: BackgroundTasks, db: Database = Depends(get_db)):
    background.add_task(_send_email_safely, db, order)  # runs after the response is sent
    logger.info("Order created (v2): item=%s quantity=%s", order.item, order.quantity)
    return {"version": "v2", "status": "created", "item": order.item, "quantity": order.quantity}
