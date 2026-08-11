from fabcopilot.application.services.approval import ApprovalService
from fabcopilot.application.services.knowledge import SearchKnowledgeService
from fabcopilot.application.services.natural_language_query import (
    NaturalLanguageQueryService,
)
from fabcopilot.domain.agent import ToolDefinition
from fabcopilot.domain.approval import MaintenanceActionType
from fabcopilot.domain.equipment import EquipmentType


class FabAgentToolRegistry:
    def __init__(
        self,
        knowledge_search: SearchKnowledgeService,
        analytics_query: NaturalLanguageQueryService,
        approval_service: ApprovalService,
    ) -> None:
        self._knowledge_search = knowledge_search
        self._analytics_query = analytics_query
        self._approval_service = approval_service

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return (
            ToolDefinition(
                name="search_knowledge",
                description=(
                    "Search diffusion furnace maintenance knowledge with hybrid "
                    "keyword and vector retrieval."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "equipment_type": {
                            "type": "string",
                            "enum": [item.value for item in EquipmentType],
                        },
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["query", "equipment_type", "limit"],
                    "additionalProperties": False,
                },
            ),
            ToolDefinition(
                name="query_analytics",
                description=(
                    "Answer a structured equipment, process-run, yield, or alarm "
                    "question through guarded read-only NL2SQL."
                ),
                parameters={
                    "type": "object",
                    "properties": {"question": {"type": "string"}},
                    "required": ["question"],
                    "additionalProperties": False,
                },
            ),
            ToolDefinition(
                name="propose_maintenance_action",
                description=(
                    "Propose a high-risk maintenance action. This only creates a "
                    "pending human approval and never executes equipment changes."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "equipment_id": {"type": "string"},
                        "action_type": {
                            "type": "string",
                            "enum": [item.value for item in MaintenanceActionType],
                        },
                        "reason": {"type": "string"},
                        "parameters": {"type": "object"},
                    },
                    "required": [
                        "equipment_id",
                        "action_type",
                        "reason",
                        "parameters",
                    ],
                    "additionalProperties": False,
                },
            ),
        )

    def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        if name == "search_knowledge":
            return self._execute_knowledge_search(arguments)
        if name == "query_analytics":
            return self._execute_analytics_query(arguments)
        if name == "propose_maintenance_action":
            return self._execute_maintenance_proposal(arguments)
        raise ValueError(f"unknown agent tool '{name}'")

    def _execute_knowledge_search(
        self,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        results = self._knowledge_search.execute(
            query=self._required_string(arguments, "query"),
            equipment_type=EquipmentType(
                self._required_string(arguments, "equipment_type")
            ),
            limit=self._required_integer(arguments, "limit"),
        )
        return {
            "results": [
                {
                    "document_id": result.document.document_id,
                    "title": result.document.title,
                    "content": result.document.content,
                    "source": result.document.source,
                    "score": result.score,
                }
                for result in results
            ]
        }

    def _execute_analytics_query(
        self,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        result = self._analytics_query.execute(
            self._required_string(arguments, "question")
        )
        return {
            "sql": result.sql,
            "columns": list(result.columns),
            "rows": list(result.rows),
            "truncated": result.truncated,
            "elapsed_ms": result.elapsed_ms,
        }

    def _execute_maintenance_proposal(
        self,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        raw_parameters = arguments.get("parameters")
        if not isinstance(raw_parameters, dict):
            raise ValueError("parameters must be an object")
        approval = self._approval_service.request(
            equipment_id=self._required_string(arguments, "equipment_id"),
            action_type=MaintenanceActionType(
                self._required_string(arguments, "action_type")
            ),
            reason=self._required_string(arguments, "reason"),
            parameters=raw_parameters,
        )
        return {
            "approval_id": approval.approval_id,
            "status": approval.status.value,
            "message": "Action requires explicit human approval and was not executed.",
        }

    @staticmethod
    def _required_string(arguments: dict[str, object], name: str) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-blank string")
        return value

    @staticmethod
    def _required_integer(arguments: dict[str, object], name: str) -> int:
        value = arguments.get(name)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
        return value
