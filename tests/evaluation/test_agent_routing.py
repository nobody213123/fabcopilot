from pathlib import Path

from fabcopilot.evaluation.agent_routing import evaluate_agent_routing, load_cases


def test_offline_agent_routing_evaluation() -> None:
    cases_path = (
        Path(__file__).resolve().parents[2] / "evals" / "agent_routing_cases.json"
    )

    result = evaluate_agent_routing(load_cases(cases_path))

    assert result.cases == 6
    assert result.exact_tool_routing_accuracy == 1.0
    assert result.approval_safety_accuracy == 1.0
