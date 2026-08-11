import pytest

from fabcopilot.application.exceptions import InvalidApprovalTransitionError
from fabcopilot.application.services.approval import ApprovalService
from fabcopilot.domain.approval import (
    ApprovalRequest,
    ApprovalStatus,
    MaintenanceActionType,
)


class InMemoryApprovalRepository:
    def __init__(self) -> None:
        self.requests: dict[str, ApprovalRequest] = {}

    def save(self, request: ApprovalRequest) -> None:
        self.requests[request.approval_id] = request

    def get_by_id(self, approval_id: str) -> ApprovalRequest | None:
        return self.requests.get(approval_id)

    def save_decision_if_pending(self, request: ApprovalRequest) -> bool:
        current = self.requests.get(request.approval_id)
        if current is None or current.status is not ApprovalStatus.PENDING:
            return False
        self.requests[request.approval_id] = request
        return True


def test_approval_requires_explicit_human_decision() -> None:
    repository = InMemoryApprovalRepository()
    service = ApprovalService(repository)
    pending = service.request(
        equipment_id="DF-01",
        action_type=MaintenanceActionType.PAUSE_EQUIPMENT,
        reason="Critical temperature excursion",
        parameters={},
    )

    approved = service.decide(
        approval_id=pending.approval_id,
        decision=ApprovalStatus.APPROVED,
        decided_by="shift-supervisor",
        decision_note="Verified alarm history",
    )

    assert pending.status is ApprovalStatus.PENDING
    assert approved.status is ApprovalStatus.APPROVED
    assert approved.decided_by == "shift-supervisor"
    assert approved.decided_at is not None


def test_approval_cannot_be_decided_twice() -> None:
    repository = InMemoryApprovalRepository()
    service = ApprovalService(repository)
    pending = service.request(
        equipment_id="DF-01",
        action_type=MaintenanceActionType.SCHEDULE_INSPECTION,
        reason="Inspect thermocouple drift",
        parameters={},
    )
    service.decide(
        approval_id=pending.approval_id,
        decision=ApprovalStatus.REJECTED,
        decided_by="shift-supervisor",
    )

    with pytest.raises(InvalidApprovalTransitionError):
        service.decide(
            approval_id=pending.approval_id,
            decision=ApprovalStatus.APPROVED,
            decided_by="another-supervisor",
        )
