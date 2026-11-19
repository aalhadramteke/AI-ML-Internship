"""Simulated infrastructure: a 'database' and an 'email service' with sync and async methods."""
import asyncio
import time

from app.settings import settings


class Database:
    # ---- synchronous (v1) ----
    def fetch_item(self, item_id: int) -> dict:
        time.sleep(settings.db_delay)
        return {"id": item_id, "name": f"item-{item_id}"}

    def call_external(self, item_id: int) -> dict:
        time.sleep(settings.external_delay)
        return {"id": item_id, "stock": 42}

    def send_email(self, order) -> None:
        time.sleep(settings.email_delay)

    # ---- asynchronous (v2) ----
    async def afetch_item(self, item_id: int) -> dict:
        await asyncio.sleep(settings.db_delay)
        return {"id": item_id, "name": f"item-{item_id}"}

    async def acall_external(self, item_id: int) -> dict:
        await asyncio.sleep(settings.external_delay)
        return {"id": item_id, "stock": 42}

    async def asend_email(self, order) -> None:
        await asyncio.sleep(settings.email_delay)


_db = Database()


def get_db() -> Database:
    return _db
