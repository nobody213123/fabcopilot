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
        knowledge_results: list[dict[str, object]] = []
        analytics_output: dict[str, object] | None = None
        for output in tool_outputs:
            raw_results = output.output.get("results")
            if isinstance(raw_results, list):
                knowledge_results.extend(
                    item for item in raw_results if isinstance(item, dict)
                )
            if "sql" in output.output:
                analytics_output = output.output

        uses_chinese = bool(re.search(r"[\u4e00-\u9fff]", prompt))
        answer = self._compose_evidence_answer(
            prompt=prompt,
            knowledge_results=knowledge_results,
            analytics_output=analytics_output,
            approval_pending=approval_pending,
            uses_chinese=uses_chinese,
        )
        return AgentModelResponse(
            response_id=str(uuid4()),
            text=answer,
            tool_calls=(),
        )

    @staticmethod
    def _compose_evidence_answer(
        prompt: str,
        knowledge_results: list[dict[str, object]],
        analytics_output: dict[str, object] | None,
        approval_pending: bool,
        uses_chinese: bool,
    ) -> str:
        top = knowledge_results[0] if knowledge_results else None
        rows = analytics_output.get("rows", []) if analytics_output else []
        row_count = len(rows) if isinstance(rows, list) else 0
        if uses_chinese:
            parts = [f"已完成诊断证据收集：{prompt}。"]
            if top:
                parts.append(
                    f"首要知识证据为《{top.get('title', '未知文档')}》"
                    f"（来源：{top.get('source', 'unknown')}）："
                    f"{str(top.get('content', ''))[:240]}"
                )
            else:
                parts.append("未检索到可引用的维护知识，当前不能给出可靠根因。")
            if analytics_output:
                parts.append(
                    f"受限只读查询返回 {row_count} 行数据；SQL 与完整结果保存在工具轨迹中。"
                )
            if approval_pending:
                parts.append("高风险维护提案已进入人工审批，设备操作尚未执行。")
            else:
                parts.append("本回答仅提供诊断证据与检查建议，不代表已执行设备操作。")
            return "".join(parts)

        parts = [f"Evidence was collected for: {prompt}. "]
        if top:
            parts.append(
                f"The leading knowledge source is '{top.get('title', 'unknown')}' "
                f"({top.get('source', 'unknown')}): "
                f"{str(top.get('content', ''))[:240]} "
            )
        else:
            parts.append(
                "No citable maintenance knowledge was retrieved, so a reliable root "
                "cause cannot yet be stated. "
            )
        if analytics_output:
            parts.append(
                f"The guarded read-only query returned {row_count} row(s); its SQL and "
                "full result remain in the tool trace. "
            )
        parts.append(
            "A maintenance proposal is pending human approval and was not executed."
            if approval_pending
            else "This diagnosis did not execute any equipment action."
        )
        return "".join(parts)


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
