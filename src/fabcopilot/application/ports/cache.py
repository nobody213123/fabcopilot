from typing import Protocol


class JsonCache(Protocol):
    def get_json(self, key: str) -> dict[str, object] | None: ...

    def set_json(
        self,
        key: str,
        value: dict[str, object],
        ttl_seconds: int,
    ) -> None: ...

    def ping(self) -> bool: ...
