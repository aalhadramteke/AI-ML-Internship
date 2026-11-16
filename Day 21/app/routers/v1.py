from fastapi import APIRouter, Depends
from app.deps import Database, get_db
from app.schemas import OrderIn

router = APIRouter()

@router.get("/report/{item_id}")
def report(item_id: int, db: Database = Depends(get_db)):
    item = db.fetch_item(item_id)    # 0.3s
    price = db.fetch_price(item_id)  # 0.2s, runs after the first call
    return {**item, "price": price}

@router.post("/orders", status_code=201)
def create_order(order: OrderIn, db: Database = Depends(get_db)):
    db.send_email(order.item)  # blocks the response for 2s
    return {"status": "created", "item": order.item}