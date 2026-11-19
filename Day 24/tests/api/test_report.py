import pytest

from app.settings import settings


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_report_ok(client, version):
    r = client.get(f"/api/{version}/report/1")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == version
    assert body["item"]["id"] == 1
    assert "external" in body


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_report_item_id_must_be_integer(client, version):
    assert client.get(f"/api/{version}/report/abc").status_code == 422


def test_v1_and_v2_return_same_data(client):
    v1 = client.get("/api/v1/report/5").json()
    v2 = client.get("/api/v2/report/5").json()
    assert v1["item"] == v2["item"]
    assert v1["external"] == v2["external"]


def test_v2_overlaps_io_so_it_is_faster_than_v1(client, monkeypatch):
    monkeypatch.setattr(settings, "db_delay", 0.15)
    monkeypatch.setattr(settings, "external_delay", 0.15)
    t1 = float(client.get("/api/v1/report/1").headers["X-Process-Time-ms"])
    t2 = float(client.get("/api/v2/report/1").headers["X-Process-Time-ms"])
    assert t1 >= 300            # 0.15 + 0.15, one after the other
    assert t2 < t1 * 0.8        # overlapped with asyncio.gather
