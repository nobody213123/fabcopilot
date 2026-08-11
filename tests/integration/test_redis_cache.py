import uuid

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from fabcopilot.api.app import app
from fabcopilot.config import Settings
from fabcopilot.infrastructure.cache import RedisJsonCache

pytestmark = pytest.mark.integration


def test_redis_cache_round_trip() -> None:
    client = Redis.from_url(Settings().redis_url, decode_responses=True)
    cache = RedisJsonCache(client)
    key = f"integration:test:{uuid.uuid4()}"

    try:
        cache.set_json(key, {"status": "ok"}, ttl_seconds=30)

        assert cache.get_json(key) == {"status": "ok"}
        assert cache.ping() is True
    finally:
        client.delete(key)
        client.close()


def test_readiness_reports_postgres_and_redis() -> None:
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["checks"] == {"postgres": True, "redis": True}
