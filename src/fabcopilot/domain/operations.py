from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ProcessRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"


class AlarmSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ProcessRun:
    run_id: str
    equipment_id: str
    lot_id: str
    recipe: str
    started_at: datetime
    status: ProcessRunStatus
    ended_at: datetime | None = None
    yield_rate: float | None = None

    def __post_init__(self) -> None:
        for field_name in ("run_id", "equipment_id", "lot_id", "recipe"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be blank")
        if self.yield_rate is not None and not 0.0 <= self.yield_rate <= 1.0:
            raise ValueError("yield_rate must be between 0 and 1")
        if self.ended_at is not None and self.ended_at <= self.started_at:
            raise ValueError("ended_at must be after started_at")


@dataclass(frozen=True)
class AlarmEvent:
    event_id: str
    equipment_id: str
    alarm_code: str
    severity: AlarmSeverity
    message: str
    occurred_at: datetime
    cleared_at: datetime | None = None

    def __post_init__(self) -> None:
        for field_name in ("event_id", "equipment_id", "alarm_code", "message"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be blank")
        if self.cleared_at is not None and self.cleared_at < self.occurred_at:
            raise ValueError("cleared_at must not be before occurred_at")
