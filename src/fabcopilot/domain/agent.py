from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, object]


@dataclass(frozen=True)
class AgentToolCall:
    call_id: str
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True)
class ToolCallOutput:
    call_id: str
    output: dict[str, object]


@dataclass(frozen=True)
class AgentModelResponse:
    response_id: str
    text: str | None
    tool_calls: tuple[AgentToolCall, ...]


@dataclass(frozen=True)
class AgentToolTrace:
    name: str
    arguments: dict[str, object]
    output: dict[str, object]


@dataclass(frozen=True)
class DiagnosticAgentResult:
    answer: str
    tool_trace: tuple[AgentToolTrace, ...]
    pending_approval_ids: tuple[str, ...]
