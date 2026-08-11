from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session
from sqlglot import exp, parse
from sqlglot.errors import ParseError

from fabcopilot.domain.analytics import AnalyticsQueryResult, JsonScalar

DEFAULT_ALLOWED_TABLES = frozenset(
    {
        "equipment",
        "process_run",
        "alarm_event",
    }
)
_ALLOWED_FUNCTIONS = frozenset(
    {
        "avg",
        "coalesce",
        "count",
        "date_trunc",
        "lower",
        "max",
        "min",
        "nullif",
        "round",
        "sum",
        "timestamp_trunc",
        "upper",
    }
)


class UnsafeSqlError(ValueError):
    pass


class SqlGlotSafetyValidator:
    def __init__(
        self,
        allowed_tables: frozenset[str] = DEFAULT_ALLOWED_TABLES,
        max_rows: int = 200,
    ) -> None:
        self._allowed_tables = allowed_tables
        self._max_rows = max_rows

    def validate(self, sql: str) -> str:
        try:
            statements = [item for item in parse(sql, read="postgres") if item]
        except ParseError as exc:
            raise UnsafeSqlError("SQL could not be parsed") from exc

        if len(statements) != 1:
            raise UnsafeSqlError("exactly one SQL statement is required")

        expression = statements[0]
        if not isinstance(expression, exp.Query):
            raise UnsafeSqlError("only read-only query statements are allowed")
        if any(expression.find_all(exp.DML)) or any(expression.find_all(exp.DDL)):
            raise UnsafeSqlError("data modification and DDL are forbidden")
        if any(expression.find_all(exp.Command)):
            raise UnsafeSqlError("SQL commands are forbidden")

        self._validate_stars(expression)
        self._validate_tables(expression)
        self._validate_functions(expression)
        expression = self._enforce_limit(expression)
        return expression.sql(dialect="postgres")

    @staticmethod
    def _validate_stars(expression: exp.Expression) -> None:
        for star in expression.find_all(exp.Star):
            if not isinstance(star.parent, exp.Count):
                raise UnsafeSqlError("SELECT * is forbidden; name required columns")

    def _validate_tables(self, expression: exp.Expression) -> None:
        cte_names = {cte.alias_or_name.lower() for cte in expression.find_all(exp.CTE)}
        for table in expression.find_all(exp.Table):
            table_name = table.name.lower()
            if table_name in cte_names:
                continue
            if table.db and table.db.lower() != "public":
                raise UnsafeSqlError("only the public schema is allowed")
            if table_name not in self._allowed_tables:
                raise UnsafeSqlError(f"table '{table_name}' is not allowed")

    @staticmethod
    def _validate_functions(expression: exp.Expression) -> None:
        for function in expression.find_all(exp.Func):
            function_name = function.sql_name().lower()
            if isinstance(function, exp.Anonymous):
                function_name = function.name.lower()
            if function_name not in _ALLOWED_FUNCTIONS:
                raise UnsafeSqlError(
                    f"function '{function_name}' is not in the analytics allowlist"
                )

    def _enforce_limit(self, expression: exp.Query) -> exp.Query:
        limit = expression.args.get("limit")
        if limit is None:
            return expression.limit(self._max_rows)

        limit_expression = limit.expression
        if not isinstance(limit_expression, exp.Literal) or not limit_expression.is_int:
            raise UnsafeSqlError("LIMIT must be a literal integer")
        if int(limit_expression.this) > self._max_rows:
            return expression.limit(self._max_rows)
        return expression


class RuleBasedSqlGenerator:
    """Offline baseline; a model-backed generator can replace this port."""

    def generate(self, question: str) -> str:
        normalized = question.casefold()
        equipment_id = self._extract_equipment_id(question)
        equipment_filter = (
            f" WHERE equipment_id = '{equipment_id}'" if equipment_id else ""
        )
        if "报警" in normalized or "alarm" in normalized:
            return (
                "SELECT event_id, equipment_id, alarm_code, severity, message, "
                "occurred_at, cleared_at FROM alarm_event"
                f"{equipment_filter} "
                "ORDER BY occurred_at DESC LIMIT 50"
            )
        if ("平均" in normalized or "average" in normalized) and (
            "良率" in normalized or "yield" in normalized
        ):
            return (
                "SELECT equipment_id, ROUND(AVG(yield_rate), 4) AS average_yield, "
                "COUNT(*) AS run_count FROM process_run "
                "WHERE yield_rate IS NOT NULL"
                f"{' AND equipment_id = ' + repr(equipment_id) if equipment_id else ''} "
                "GROUP BY equipment_id "
                "ORDER BY average_yield ASC"
            )
        if "良率" in normalized or "yield" in normalized:
            return (
                "SELECT run_id, equipment_id, lot_id, recipe, yield_rate, "
                "started_at FROM process_run WHERE yield_rate IS NOT NULL"
                f"{' AND equipment_id = ' + repr(equipment_id) if equipment_id else ''} "
                "ORDER BY yield_rate ASC, started_at DESC LIMIT 50"
            )
        if equipment_id:
            return (
                "SELECT run_id, equipment_id, lot_id, recipe, yield_rate, started_at "
                "FROM process_run "
                f"WHERE equipment_id = '{equipment_id}' "
                "ORDER BY started_at DESC LIMIT 20"
            )
        return (
            "SELECT equipment_id, equipment_type FROM equipment "
            "ORDER BY equipment_id LIMIT 50"
        )

    @staticmethod
    def _extract_equipment_id(question: str) -> str | None:
        match = re.search(r"\b[A-Za-z]{2,}-[A-Za-z0-9-]+\b", question)
        return match.group(0).upper() if match else None


class SqlAlchemyReadOnlyQueryExecutor:
    def __init__(
        self,
        session: Session,
        max_rows: int = 200,
        statement_timeout_ms: int = 3000,
    ) -> None:
        self._session = session
        self._max_rows = max_rows
        self._statement_timeout_ms = statement_timeout_ms

    def execute(self, sql: str) -> AnalyticsQueryResult:
        self._session.execute(text("SET TRANSACTION READ ONLY"))
        self._session.execute(
            text(f"SET LOCAL statement_timeout = {self._statement_timeout_ms}")
        )

        started_at = perf_counter()
        result = self._session.execute(text(sql))
        raw_rows = result.fetchmany(self._max_rows + 1)
        elapsed_ms = (perf_counter() - started_at) * 1000
        truncated = len(raw_rows) > self._max_rows
        rows = raw_rows[: self._max_rows]
        columns = tuple(result.keys())

        return AnalyticsQueryResult(
            sql=sql,
            columns=columns,
            rows=tuple(self._serialize_row(row) for row in rows),
            truncated=truncated,
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _serialize_row(row: Row[tuple[object, ...]]) -> dict[str, JsonScalar]:
        return {
            key: SqlAlchemyReadOnlyQueryExecutor._serialize_value(value)
            for key, value in row._mapping.items()
        }

    @staticmethod
    def _serialize_value(value: object) -> JsonScalar:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)
