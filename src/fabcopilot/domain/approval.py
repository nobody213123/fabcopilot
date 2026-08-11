from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MaintenanceActionType(StrEnum):
    PAUSE_EQUIPMENT = "pause_equipment"
    SCHEDULE_INSPECTION = "schedule_inspection"
    ADJUST_RECIPE = "adjust_recipe"


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    equipment_id: str
    action_type: MaintenanceActionType
    reason: str
    parameters: dict[str, object]
    status: ApprovalStatus
    requested_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision_note: str | None = None
