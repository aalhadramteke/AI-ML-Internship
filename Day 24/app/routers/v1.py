import logging

from fastapi import APIRouter, Depends

from app.deps import Database, get_db
from app.schemas import OrderIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["v1 (sync)"])


@router.get("/report/{item_id}")
def report(item_id: int, db: Database = Depends(get_db)):
    item = db.fetch_item(item_id)          # DB call ...
    external = db.call_external(item_id)   # ... then external call, one after the other
    return {"version": "v1", "item": item, "external": external}


@router.post("/orders", status_code=201)
def create_order(order: OrderIn, db: Database = Depends(get_db)):
    db.send_email(order)  # inline: the response waits for the email
    logger.info("Order created (v1): item=%s quantity=%s", order.item, order.quantity)
    return {"version": "v1", "status": "created", "item": order.item, "quantity": order.quantity}
