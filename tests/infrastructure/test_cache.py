from fabcopilot.infrastructure.cache import RedisJsonCache


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ex: int) -> bool:
        self.values[key] = value
        return True

    def ping(self) -> bool:
        return True

    def incr(self, key: str) -> int:
        value = int(self.values.get(key, "0")) + 1
        self.values[key] = str(value)
        return value


def test_redis_cache_round_trips_json() -> None:
    cache = RedisJsonCache(FakeRedis())  # type: ignore[arg-type]

    cache.set_json("diagnosis:1", {"answer": "stable"}, ttl_seconds=60)

    assert cache.get_json("diagnosis:1") == {"answer": "stable"}
    assert cache.ping() is True
    assert cache.get_version("knowledge") == 0
    assert cache.bump_version("knowledge") == 1
    assert cache.get_version("knowledge") == 1
