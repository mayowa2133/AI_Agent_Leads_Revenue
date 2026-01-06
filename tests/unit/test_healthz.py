from fastapi.testclient import TestClient

from src.api.main import create_app


def test_healthz():
    client = TestClient(create_app())
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_routes_registered():
    client = TestClient(create_app())
    resp = client.get("/openapi.json")
    assert resp.status_code == 200


