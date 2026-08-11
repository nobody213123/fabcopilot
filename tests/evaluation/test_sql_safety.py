from pathlib import Path

from fabcopilot.evaluation.sql_safety import evaluate_sql_safety


def test_sql_safety_evaluation_has_no_known_regressions() -> None:
    project_root = Path(__file__).resolve().parents[2]

    result = evaluate_sql_safety(project_root / "evals" / "sql_safety_cases.json")

    assert result.safe_cases >= 8
    assert result.unsafe_cases >= 15
    assert result.safe_acceptance_rate == 1.0
    assert result.unsafe_rejection_rate == 1.0
