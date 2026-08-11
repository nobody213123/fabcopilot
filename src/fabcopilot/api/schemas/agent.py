from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from fabcopilot.domain.approval import ApprovalStatus, MaintenanceActionType


class DiagnosticAgentRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prompt must not be blank")
        return value


class AgentToolTraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    arguments: dict[str, object]
    output: dict[str, object]


class DiagnosticEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    reference_id: str
    source: str
    summary: str


class DiagnosticAgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    answer: str
    tool_trace: tuple[AgentToolTraceResponse, ...]
    pending_approval_ids: tuple[str, ...]
    evidence: tuple[DiagnosticEvidenceResponse, ...] = ()
    missing_evidence: tuple[str, ...] = ()


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalStatus
    decided_by: str
    decision_note: str | None = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: ApprovalStatus) -> ApprovalStatus:
        if value not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
            raise ValueError("decision must be approved or rejected")
        return value

    @field_validator("decided_by")
    @classmethod
    def validate_decided_by(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("decided_by must not be blank")
        return value


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_id: str
    equipment_id: str
    action_type: MaintenanceActionType
    reason: str
    parameters: dict[str, object]
    status: ApprovalStatus
    requested_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    decision_note: str | None
