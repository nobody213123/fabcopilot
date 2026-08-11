import pytest

from fabcopilot.infrastructure.nl2sql import (
    RuleBasedSqlGenerator,
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
        "SELECT pg_read_binary_file('/etc/passwd')",
        "SELECT query_to_xml('SELECT usename FROM pg_user', true, true, '')",
        "SELECT lo_get(1)",
        "SELECT current_setting('data_directory')",
        "SELECT repeat('x', 100000000)",
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


def test_rule_generator_scopes_equipment_query_to_requested_id() -> None:
    sql = RuleBasedSqlGenerator().generate(
        "Analyze DF-02 temperature uniformity and provide evidence"
    )

    assert "WHERE equipment_id = 'DF-02'" in sql
    assert "FROM process_run" in sql


def test_rule_generator_scopes_alarm_query_to_requested_id() -> None:
    sql = RuleBasedSqlGenerator().generate("检查 DF-03 最近的报警")

    assert "FROM alarm_event WHERE equipment_id = 'DF-03'" in sql
