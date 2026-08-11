from dataclasses import dataclass
from typing import TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None


@dataclass(frozen=True)
class AnalyticsQueryResult:
    sql: str
    columns: tuple[str, ...]
    rows: tuple[dict[str, JsonScalar], ...]
    truncated: bool
    elapsed_ms: float
