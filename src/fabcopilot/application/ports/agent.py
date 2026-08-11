from typing import Protocol

from fabcopilot.domain.agent import (
    AgentModelResponse,
    ToolCallOutput,
    ToolDefinition,
)


class AgentModel(Protocol):
    def start(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
    ) -> AgentModelResponse: ...

    def continue_with_tool_outputs(
        self,
        previous_response_id: str,
        tool_outputs: tuple[ToolCallOutput, ...],
        tools: tuple[ToolDefinition, ...],
    ) -> AgentModelResponse: ...


class AgentToolRegistry(Protocol):
    @property
    def definitions(self) -> tuple[ToolDefinition, ...]: ...

    def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]: ...
