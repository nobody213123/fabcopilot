import json
from dataclasses import asdict, dataclass
from pathlib import Path

from fabcopilot.infrastructure.nl2sql import SqlGlotSafetyValidator, UnsafeSqlError


@dataclass(frozen=True)
class SqlSafetyResult:
    cases: int
    safe_cases: int
    unsafe_cases: int
    safe_acceptance_rate: float
    unsafe_rejection_rate: float
    overall_accuracy: float
    failures: tuple[str, ...]


def evaluate_sql_safety(path: Path) -> SqlSafetyResult:
    cases = json.loads(path.read_text(encoding="utf-8"))
    validator = SqlGlotSafetyValidator()
    failures: list[str] = []
    safe_total = 0
    safe_correct = 0
    unsafe_total = 0
    unsafe_correct = 0
    for case in cases:
        expected_safe = bool(case["safe"])
        if expected_safe:
            safe_total += 1
        else:
            unsafe_total += 1
        try:
            validator.validate(case["sql"])
            accepted = True
        except UnsafeSqlError:
            accepted = False

        if accepted == expected_safe:
            if expected_safe:
                safe_correct += 1
            else:
                unsafe_correct += 1
        else:
            failures.append(case["case_id"])

    total = len(cases)
    correct = safe_correct + unsafe_correct
    return SqlSafetyResult(
        cases=total,
        safe_cases=safe_total,
        unsafe_cases=unsafe_total,
        safe_acceptance_rate=safe_correct / safe_total,
        unsafe_rejection_rate=unsafe_correct / unsafe_total,
        overall_accuracy=correct / total,
        failures=tuple(failures),
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    result = evaluate_sql_safety(project_root / "evals" / "sql_safety_cases.json")
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
