import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import research as research_router


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_research_slots():
    research_router._active = 0
    yield
    research_router._active = 0
