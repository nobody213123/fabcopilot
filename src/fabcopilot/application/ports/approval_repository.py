from typing import Protocol

from fabcopilot.domain.approval import ApprovalRequest


class ApprovalRepository(Protocol):
    def save(self, request: ApprovalRequest) -> None: ...

    def get_by_id(self, approval_id: str) -> ApprovalRequest | None: ...
