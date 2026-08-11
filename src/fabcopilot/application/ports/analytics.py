from typing import Protocol

from fabcopilot.domain.analytics import AnalyticsQueryResult


class SqlGenerator(Protocol):
    def generate(self, question: str) -> str: ...


class SqlValidator(Protocol):
    def validate(self, sql: str) -> str: ...


class ReadOnlyQueryExecutor(Protocol):
    def execute(self, sql: str) -> AnalyticsQueryResult: ...
