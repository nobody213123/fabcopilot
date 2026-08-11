import pytest

from fabcopilot.infrastructure.nl2sql import (
    SqlGlotSafetyValidator,
    UnsafeSqlError,
)


def test_validator_adds_bounded_limit_to_safe_query() -> None:
    validator = SqlGlotSafetyValidator(max_rows=100)

    sql = validator.validate(
        "SELECT equipment_id, AVG(yield_rate) FROM process_run GROUP BY equipment_id"
    )

    assert sql.endswith("LIMIT 100")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM process_run",
        "SELECT run_id FROM process_run; DROP TABLE equipment",
        "SELECT * FROM process_run",
        "SELECT secret FROM pg_catalog.pg_user",
        "SELECT pg_sleep(10) FROM process_run",
    ],
)
def test_validator_rejects_unsafe_sql(sql: str) -> None:
    validator = SqlGlotSafetyValidator()

    with pytest.raises(UnsafeSqlError):
        validator.validate(sql)


def test_validator_allows_count_star() -> None:
    validator = SqlGlotSafetyValidator()

    sql = validator.validate("SELECT COUNT(*) AS run_count FROM process_run")

    assert "COUNT(*)" in sql
