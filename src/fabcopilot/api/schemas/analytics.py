from pydantic import BaseModel, field_validator

from fabcopilot.domain.analytics import JsonScalar


class AnalyticsQueryRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value


class AnalyticsQueryResponse(BaseModel):
    sql: str
    columns: tuple[str, ...]
    rows: tuple[dict[str, JsonScalar], ...]
    truncated: bool
    elapsed_ms: float
