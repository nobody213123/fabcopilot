import json

import structlog
from prometheus_client import Counter
from redis import Redis
from redis.exceptions import RedisError

logger = structlog.get_logger()

CACHE_OPERATIONS = Counter(
    "fabcopilot_cache_operations_total",
    "Redis cache operations grouped by outcome.",
    ("operation", "outcome"),
)


class RedisJsonCache:
    def __init__(self, client: Redis) -> None:
        self._client = client

    def get_json(self, key: str) -> dict[str, object] | None:
        try:
            raw_value = self._client.get(key)
        except RedisError as exc:
            CACHE_OPERATIONS.labels("get", "error").inc()
            logger.warning("cache_get_failed", error=str(exc))
            return None

        if raw_value is None:
            CACHE_OPERATIONS.labels("get", "miss").inc()
            return None
        try:
            value = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError) as exc:
            CACHE_OPERATIONS.labels("get", "invalid").inc()
            logger.warning("cache_value_invalid", error=str(exc))
            return None
        if not isinstance(value, dict):
            CACHE_OPERATIONS.labels("get", "invalid").inc()
            return None
        CACHE_OPERATIONS.labels("get", "hit").inc()
        return value

    def set_json(
        self,
        key: str,
        value: dict[str, object],
        ttl_seconds: int,
    ) -> None:
        try:
            self._client.set(key, json.dumps(value), ex=ttl_seconds)
            CACHE_OPERATIONS.labels("set", "success").inc()
        except RedisError as exc:
            CACHE_OPERATIONS.labels("set", "error").inc()
            logger.warning("cache_set_failed", error=str(exc))

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            return False
