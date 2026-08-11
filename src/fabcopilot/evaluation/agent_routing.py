import json
from dataclasses import asdict, dataclass
from pathlib import Path

from fabcopilot.infrastructure.agent_models import RuleBasedDiagnosticAgentModel


@dataclass(frozen=True)
class RoutingCase:
    case_id: str
    prompt: str
    expected_tools: tuple[str, ...]
    approval_required: bool


@dataclass(frozen=True)
class EvaluationResult:
    cases: int
    exact_tool_routing_accuracy: float
    approval_safety_accuracy: float


def load_cases(path: Path) -> tuple[RoutingCase, ...]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        RoutingCase(
            case_id=item["case_id"],
            prompt=item["prompt"],
            expected_tools=tuple(item["expected_tools"]),
            approval_required=item["approval_required"],
        )
        for item in raw_cases
    )


def evaluate_agent_routing(cases: tuple[RoutingCase, ...]) -> EvaluationResult:
    model = RuleBasedDiagnosticAgentModel()
    exact_matches = 0
    safety_matches = 0
    for case in cases:
        response = model.start(case.prompt, ())
        actual_tools = tuple(call.name for call in response.tool_calls)
        exact_matches += actual_tools == case.expected_tools
        actual_requires_approval = "propose_maintenance_action" in actual_tools
        safety_matches += actual_requires_approval == case.approval_required

    total = len(cases)
    if total == 0:
        raise ValueError("evaluation requires at least one case")
    return EvaluationResult(
        cases=total,
        exact_tool_routing_accuracy=exact_matches / total,
        approval_safety_accuracy=safety_matches / total,
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    cases = load_cases(project_root / "evals" / "agent_routing_cases.json")
    print(json.dumps(asdict(evaluate_agent_routing(cases)), indent=2))


if __name__ == "__main__":
    main()
