import asyncio
import time

class Database:
    # Sync versions (blocking), used by v1
    def fetch_item(self, item_id: int):
        time.sleep(0.3)  # simulated DB query
        return {"id": item_id, "name": f"item-{item_id}"}

    def fetch_price(self, item_id: int):
        time.sleep(0.2)  # simulated external API call
        return 99.0

    def send_email(self, item: str):
        time.sleep(2)  # simulated slow email service

    # Async versions (non-blocking), used by v2
    async def afetch_item(self, item_id: int):
        await asyncio.sleep(0.3)
        return {"id": item_id, "name": f"item-{item_id}"}

    async def afetch_price(self, item_id: int):
        await asyncio.sleep(0.2)
        return 99.0

    async def asend_email(self, item: str):
        await asyncio.sleep(2)
        print(f"[background] email sent for {item}")

_db = Database()

def get_db() -> Database:
    return _db