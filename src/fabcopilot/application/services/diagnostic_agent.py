from fabcopilot.application.ports.agent import AgentModel, AgentToolRegistry
from fabcopilot.domain.agent import (
    AgentToolTrace,
    DiagnosticAgentResult,
    ToolCallOutput,
)


class DiagnosticAgentService:
    def __init__(
        self,
        model: AgentModel,
        tool_registry: AgentToolRegistry,
        max_steps: int = 6,
    ) -> None:
        self._model = model
        self._tool_registry = tool_registry
        self._max_steps = max_steps

    def execute(self, prompt: str) -> DiagnosticAgentResult:
        if not prompt.strip():
            raise ValueError("prompt must not be blank")

        response = self._model.start(prompt, self._tool_registry.definitions)
        trace: list[AgentToolTrace] = []
        pending_approval_ids: list[str] = []

        for _ in range(self._max_steps):
            if not response.tool_calls:
                if response.text is None:
                    raise RuntimeError(
                        "agent model returned neither text nor tool calls"
                    )
                return DiagnosticAgentResult(
                    answer=response.text,
                    tool_trace=tuple(trace),
                    pending_approval_ids=tuple(pending_approval_ids),
                )

            outputs: list[ToolCallOutput] = []
            for call in response.tool_calls:
                output = self._tool_registry.execute(call.name, call.arguments)
                trace.append(
                    AgentToolTrace(
                        name=call.name,
                        arguments=call.arguments,
                        output=output,
                    )
                )
                approval_id = output.get("approval_id")
                if output.get("status") == "pending" and isinstance(approval_id, str):
                    pending_approval_ids.append(approval_id)
                outputs.append(ToolCallOutput(call_id=call.call_id, output=output))

            response = self._model.continue_with_tool_outputs(
                previous_response_id=response.response_id,
                tool_outputs=tuple(outputs),
                tools=self._tool_registry.definitions,
            )

        raise RuntimeError("agent exceeded maximum tool-call steps")
