from fabcopilot.application.ports.agent import AgentModel, AgentToolRegistry
from fabcopilot.domain.agent import (
    AgentToolTrace,
    DiagnosticAgentResult,
    DiagnosticEvidence,
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
                    evidence=self._collect_evidence(trace),
                    missing_evidence=self._find_evidence_gaps(trace),
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

    @staticmethod
    def _collect_evidence(
        trace: list[AgentToolTrace],
    ) -> tuple[DiagnosticEvidence, ...]:
        evidence: list[DiagnosticEvidence] = []
        for item in trace:
            if item.name == "search_knowledge":
                raw_results = item.output.get("results", [])
                if not isinstance(raw_results, list):
                    continue
                for result in raw_results:
                    if not isinstance(result, dict):
                        continue
                    document_id = result.get("document_id")
                    title = result.get("title")
                    source = result.get("source")
                    if all(
                        isinstance(value, str) for value in (document_id, title, source)
                    ):
                        evidence.append(
                            DiagnosticEvidence(
                                kind="knowledge",
                                reference_id=document_id,
                                source=source,
                                summary=title,
                            )
                        )
            elif item.name == "query_analytics":
                sql = item.output.get("sql")
                rows = item.output.get("rows", [])
                if isinstance(sql, str) and isinstance(rows, list) and rows:
                    evidence.append(
                        DiagnosticEvidence(
                            kind="analytics",
                            reference_id="guarded-sql-result",
                            source=sql,
                            summary=f"{len(rows)} row(s) returned by a read-only query",
                        )
                    )
        return tuple(evidence)

    @staticmethod
    def _find_evidence_gaps(trace: list[AgentToolTrace]) -> tuple[str, ...]:
        has_knowledge = any(
            item.name == "search_knowledge" and bool(item.output.get("results"))
            for item in trace
        )
        has_analytics = any(
            item.name == "query_analytics" and bool(item.output.get("rows"))
            for item in trace
        )
        gaps: list[str] = []
        if not has_knowledge:
            gaps.append("No relevant maintenance knowledge was retrieved.")
        if not has_analytics:
            gaps.append("No matching equipment or process data was returned.")
        return tuple(gaps)
