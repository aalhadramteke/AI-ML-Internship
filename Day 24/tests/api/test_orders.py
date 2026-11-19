import logging

import pytest

from app.deps import Database

VALID = {"item": "book", "quantity": 2}

INVALID_PAYLOADS = [
    {},
    {"item": "book"},
    {"quantity": 1},
    {"item": "a", "quantity": 1},
    {"item": "x" * 51, "quantity": 1},
    {"item": "book", "quantity": 0},
    {"item": "book", "quantity": 101},
    {"item": "book", "quantity": "two"},
]


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_create_order_returns_201(client, version):
    r = client.post(f"/api/{version}/orders", json=VALID)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "created"
    assert body["item"] == "book" and body["quantity"] == 2


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_invalid_order_returns_422(client, version, payload):
    assert client.post(f"/api/{version}/orders", json=payload).status_code == 422


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize(
    "payload",
    [{"item": "ab", "quantity": 1}, {"item": "x" * 50, "quantity": 100}],
)
def test_boundary_values_are_accepted(client, version, payload):
    assert client.post(f"/api/{version}/orders", json=payload).status_code == 201


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_non_json_body_returns_422(client, version):
    r = client.post(f"/api/{version}/orders", content="not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_v1_sends_email_inline(client, monkeypatch):
    sent = []
    monkeypatch.setattr(Database, "send_email", lambda self, order: sent.append(order.item))
    assert client.post("/api/v1/orders", json=VALID).status_code == 201
    assert sent == ["book"]


def test_v2_sends_email_as_background_task(client, monkeypatch):
    sent = []

    async def fake_email(self, order):
        sent.append(order.item)

    monkeypatch.setattr(Database, "asend_email", fake_email)
    assert client.post("/api/v2/orders", json=VALID).status_code == 201
    assert sent == ["book"]


def test_v2_email_failure_does_not_break_response_and_is_logged(client, monkeypatch, caplog):
    async def failing_email(self, order):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(Database, "asend_email", failing_email)
    with caplog.at_level(logging.ERROR):
        r = client.post("/api/v2/orders", json=VALID)
    assert r.status_code == 201
    assert "Background email failed" in caplog.text
