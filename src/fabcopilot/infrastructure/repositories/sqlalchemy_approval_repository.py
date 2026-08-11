from sqlalchemy.orm import Session

from fabcopilot.application.ports.approval_repository import ApprovalRepository
from fabcopilot.domain.approval import (
    ApprovalRequest,
    ApprovalStatus,
    MaintenanceActionType,
)
from fabcopilot.infrastructure.models import ApprovalRequestRecord


class SqlAlchemyApprovalRepository(ApprovalRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, request: ApprovalRequest) -> None:
        self._session.merge(
            ApprovalRequestRecord(
                approval_id=request.approval_id,
                equipment_id=request.equipment_id,
                action_type=request.action_type.value,
                reason=request.reason,
                parameters=request.parameters,
                status=request.status.value,
                requested_at=request.requested_at,
                decided_at=request.decided_at,
                decided_by=request.decided_by,
                decision_note=request.decision_note,
            )
        )
        self._session.flush()

    def get_by_id(self, approval_id: str) -> ApprovalRequest | None:
        record = self._session.get(ApprovalRequestRecord, approval_id)
        if record is None:
            return None
        return ApprovalRequest(
            approval_id=record.approval_id,
            equipment_id=record.equipment_id,
            action_type=MaintenanceActionType(record.action_type),
            reason=record.reason,
            parameters=record.parameters,
            status=ApprovalStatus(record.status),
            requested_at=record.requested_at,
            decided_at=record.decided_at,
            decided_by=record.decided_by,
            decision_note=record.decision_note,
        )
