from fabcopilot.application.services.diagnostic_agent import DiagnosticAgentService
from fabcopilot.domain.agent import (
    AgentModelResponse,
    AgentToolCall,
    ToolCallOutput,
    ToolDefinition,
)


class ScriptedModel:
    def start(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
    ) -> AgentModelResponse:
        return AgentModelResponse(
            response_id="response-1",
            text=None,
            tool_calls=(
                AgentToolCall(
                    call_id="call-1",
                    name="propose_maintenance_action",
                    arguments={"equipment_id": "DF-01"},
                ),
            ),
        )

    def continue_with_tool_outputs(
        self,
        previous_response_id: str,
        tool_outputs: tuple[ToolCallOutput, ...],
        tools: tuple[ToolDefinition, ...],
    ) -> AgentModelResponse:
        assert previous_response_id == "response-1"
        assert tool_outputs[0].call_id == "call-1"
        return AgentModelResponse(
            response_id="response-2",
            text="Proposal created; no equipment action was executed.",
            tool_calls=(),
        )


class ScriptedRegistry:
    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return ()

    def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        assert name == "propose_maintenance_action"
        assert arguments == {"equipment_id": "DF-01"}
        return {"approval_id": "approval-1", "status": "pending"}


def test_agent_tracks_pending_human_approval() -> None:
    service = DiagnosticAgentService(ScriptedModel(), ScriptedRegistry())

    result = service.execute("Pause DF-01 after checking evidence")

    assert result.answer == "Proposal created; no equipment action was executed."
    assert result.pending_approval_ids == ("approval-1",)
    assert result.tool_trace[0].name == "propose_maintenance_action"
    assert result.evidence == ()
    assert result.missing_evidence == (
        "No relevant maintenance knowledge was retrieved.",
        "No matching equipment or process data was returned.",
    )
