import json
import re
from threading import Lock
from uuid import uuid4

from openai import OpenAI

from fabcopilot.domain.agent import (
    AgentModelResponse,
    AgentToolCall,
    ToolCallOutput,
    ToolDefinition,
)

_AGENT_INSTRUCTIONS = """You are FabCopilot, a semiconductor diffusion furnace diagnostic agent.
Use read-only evidence tools before drawing conclusions. Cite document sources and SQL evidence.
Never claim that a maintenance action was executed. High-risk actions must use the proposal tool
and remain pending until an identified human approves them.
"""


class RuleBasedDiagnosticAgentModel:
    """Deterministic offline model used when no external model key is configured."""

    def __init__(self) -> None:
        self._prompts: dict[str, str] = {}
        self._lock = Lock()

    def start(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
    ) -> AgentModelResponse:
        del tools
        response_id = str(uuid4())
        with self._lock:
            self._prompts[response_id] = prompt

        calls = [
            AgentToolCall(
                call_id=str(uuid4()),
                name="search_knowledge",
                arguments={
                    "query": prompt,
                    "equipment_type": "diffusion_furnace",
                    "limit": 5,
                },
            ),
            AgentToolCall(
                call_id=str(uuid4()),
                name="query_analytics",
                arguments={"question": prompt},
            ),
        ]
        if any(
            keyword in prompt.casefold()
            for keyword in ("停机", "停止", "pause", "stop", "调整配方")
        ):
            equipment_match = re.search(r"\b[A-Za-z]{2,}-[A-Za-z0-9-]+\b", prompt)
            equipment_id = (
                equipment_match.group(0).upper() if equipment_match else "DF-01"
            )
            calls.append(
                AgentToolCall(
                    call_id=str(uuid4()),
                    name="propose_maintenance_action",
                    arguments={
                        "equipment_id": equipment_id,
                        "action_type": "pause_equipment",
                        "reason": f"Operator requested risk review: {prompt}",
                        "parameters": {},
                    },
                )
            )

        return AgentModelResponse(
            response_id=response_id,
            text=None,
            tool_calls=tuple(calls),
        )

    def continue_with_tool_outputs(
        self,
        previous_response_id: str,
        tool_outputs: tuple[ToolCallOutput, ...],
        tools: tuple[ToolDefinition, ...],
    ) -> AgentModelResponse:
        del tools
        with self._lock:
            prompt = self._prompts.pop(previous_response_id, "diagnostic request")

        approval_pending = any(
            output.output.get("status") == "pending" for output in tool_outputs
        )
        approval_message = (
            " A maintenance proposal is pending human approval and was not executed."
            if approval_pending
            else ""
        )
        return AgentModelResponse(
            response_id=str(uuid4()),
            text=(
                f"Completed evidence collection for: {prompt}. Review the tool trace for "
                f"knowledge sources and guarded SQL results.{approval_message}"
            ),
            tool_calls=(),
        )


class OpenAIResponsesAgentModel:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def start(
        self,
        prompt: str,
        tools: tuple[ToolDefinition, ...],
    ) -> AgentModelResponse:
        response = self._client.responses.create(
            model=self._model,
            instructions=_AGENT_INSTRUCTIONS,
            input=prompt,
            tools=self._openai_tools(tools),
            tool_choice="auto",
        )
        return self._parse_response(response)

    def continue_with_tool_outputs(
        self,
        previous_response_id: str,
        tool_outputs: tuple[ToolCallOutput, ...],
        tools: tuple[ToolDefinition, ...],
    ) -> AgentModelResponse:
        response = self._client.responses.create(
            model=self._model,
            previous_response_id=previous_response_id,
            input=[
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(item.output, ensure_ascii=False),
                }
                for item in tool_outputs
            ],
            tools=self._openai_tools(tools),
            tool_choice="auto",
        )
        return self._parse_response(response)

    @staticmethod
    def _openai_tools(
        tools: tuple[ToolDefinition, ...],
    ) -> list[dict[str, object]]:
        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "strict": True,
            }
            for tool in tools
        ]

    @staticmethod
    def _parse_response(response: object) -> AgentModelResponse:
        response_id = getattr(response, "id")
        text = getattr(response, "output_text", None) or None
        tool_calls: list[AgentToolCall] = []
        for item in getattr(response, "output"):
            if getattr(item, "type", None) != "function_call":
                continue
            arguments = json.loads(getattr(item, "arguments"))
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be a JSON object")
            tool_calls.append(
                AgentToolCall(
                    call_id=getattr(item, "call_id"),
                    name=getattr(item, "name"),
                    arguments=arguments,
                )
            )
        return AgentModelResponse(
            response_id=response_id,
            text=text,
            tool_calls=tuple(tool_calls),
        )
