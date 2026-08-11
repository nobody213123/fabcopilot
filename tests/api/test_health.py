from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from fabcopilot.api.app import app
from fabcopilot.api.dependencies import get_engine, get_json_cache


class ReadyCache:
    def ping(self) -> bool:
        return True


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


def test_metrics_are_exposed(client: TestClient) -> None:
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "fabcopilot_http_requests_total" in response.text


def test_readiness_checks_database_and_cache(client: TestClient) -> None:
    engine = create_engine("sqlite://")
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_json_cache] = ReadyCache

    try:
        response = client.get("/ready")
    finally:
        app.dependency_overrides.pop(get_engine)
        app.dependency_overrides.pop(get_json_cache)
        engine.dispose()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"postgres": True, "redis": True},
    }
