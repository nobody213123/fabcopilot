from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from fabcopilot.application.exceptions import (
    ApprovalNotFoundError,
    InvalidApprovalTransitionError,
)
from fabcopilot.application.ports.approval_repository import ApprovalRepository
from fabcopilot.domain.approval import (
    ApprovalRequest,
    ApprovalStatus,
    MaintenanceActionType,
)


class ApprovalService:
    def __init__(self, repository: ApprovalRepository) -> None:
        self._repository = repository

    def request(
        self,
        equipment_id: str,
        action_type: MaintenanceActionType,
        reason: str,
        parameters: dict[str, object],
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            approval_id=str(uuid4()),
            equipment_id=equipment_id,
            action_type=action_type,
            reason=reason,
            parameters=parameters,
            status=ApprovalStatus.PENDING,
            requested_at=datetime.now(UTC),
        )
        self._repository.save(request)
        return request

    def get(self, approval_id: str) -> ApprovalRequest:
        request = self._repository.get_by_id(approval_id)
        if request is None:
            raise ApprovalNotFoundError(approval_id)
        return request

    def decide(
        self,
        approval_id: str,
        decision: ApprovalStatus,
        decided_by: str,
        decision_note: str | None = None,
    ) -> ApprovalRequest:
        request = self.get(approval_id)
        if request.status is not ApprovalStatus.PENDING:
            raise InvalidApprovalTransitionError(
                f"approval '{approval_id}' has already been decided"
            )
        if decision not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
            raise InvalidApprovalTransitionError("decision must approve or reject")
        if not decided_by.strip():
            raise ValueError("decided_by must not be blank")

        decided = replace(
            request,
            status=decision,
            decided_at=datetime.now(UTC),
            decided_by=decided_by,
            decision_note=decision_note,
        )
        if not self._repository.save_decision_if_pending(decided):
            raise InvalidApprovalTransitionError(
                f"approval '{approval_id}' has already been decided"
            )
        return decided
