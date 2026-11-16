import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends
from app.deps import Database, get_db
from app.schemas import OrderIn

router = APIRouter()

@router.get("/report/{item_id}")
async def report(item_id: int, db: Database = Depends(get_db)):
    item, price = await asyncio.gather(   # both calls run concurrently
        db.afetch_item(item_id),
        db.afetch_price(item_id),
    )
    return {**item, "price": price}

@router.post("/orders", status_code=201)
async def create_order(order: OrderIn, bg: BackgroundTasks, db: Database = Depends(get_db)):
    bg.add_task(db.asend_email, order.item)  # runs after the response is sent
    return {"status": "created", "item": order.item}