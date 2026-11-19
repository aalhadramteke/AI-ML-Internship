def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_openapi_lists_all_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in (
        "/health",
        "/api/v1/report/{item_id}",
        "/api/v2/report/{item_id}",
        "/api/v1/orders",
        "/api/v2/orders",
        "/api/v2/research",
    ):
        assert p in paths


def test_docs_page_available(client):
    assert client.get("/docs").status_code == 200
