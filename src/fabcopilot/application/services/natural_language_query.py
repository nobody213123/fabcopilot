from fabcopilot.application.ports.analytics import (
    ReadOnlyQueryExecutor,
    SqlGenerator,
    SqlValidator,
)
from fabcopilot.domain.analytics import AnalyticsQueryResult


class NaturalLanguageQueryService:
    def __init__(
        self,
        generator: SqlGenerator,
        validator: SqlValidator,
        executor: ReadOnlyQueryExecutor,
    ) -> None:
        self._generator = generator
        self._validator = validator
        self._executor = executor

    def execute(self, question: str) -> AnalyticsQueryResult:
        if not question.strip():
            raise ValueError("question must not be blank")

        generated_sql = self._generator.generate(question)
        safe_sql = self._validator.validate(generated_sql)
        return self._executor.execute(safe_sql)
