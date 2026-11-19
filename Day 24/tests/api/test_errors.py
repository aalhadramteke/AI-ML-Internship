from fastapi.testclient import TestClient

from app.main import create_app


def test_unknown_route_returns_404(client):
    assert client.get("/does-not-exist").status_code == 404


def test_wrong_method_returns_405(client):
    assert client.post("/health").status_code == 405


def test_unhandled_exception_returns_generic_500():
    app = create_app()

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["detail"] == "Internal server error"
    assert "secret internal detail" not in r.text
    assert body["request_id"]
