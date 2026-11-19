import asyncio

from app.deps import Database, get_db


def test_get_db_returns_same_instance():
    assert get_db() is get_db()
    assert isinstance(get_db(), Database)


def test_sync_methods():
    db = Database()
    assert db.fetch_item(7) == {"id": 7, "name": "item-7"}
    assert db.call_external(7)["id"] == 7
    assert db.send_email(object()) is None


def test_async_methods_match_sync_results():
    db = Database()

    async def run():
        return await asyncio.gather(db.afetch_item(7), db.acall_external(7), db.asend_email(None))

    item, external, email = asyncio.run(run())
    assert item == db.fetch_item(7)
    assert external == db.call_external(7)
    assert email is None
