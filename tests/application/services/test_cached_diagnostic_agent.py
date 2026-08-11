from fabcopilot.application.services.cached_diagnostic_agent import (
    CachedDiagnosticAgentService,
)
from fabcopilot.domain.agent import DiagnosticAgentResult


class FakeCache:
    def __init__(self) -> None:
        self.values: dict[str, dict[str, object]] = {}

    def get_json(self, key: str) -> dict[str, object] | None:
        return self.values.get(key)

    def set_json(
        self,
        key: str,
        value: dict[str, object],
        ttl_seconds: int,
    ) -> None:
        self.values[key] = value

    def ping(self) -> bool:
        return True


class StubDiagnosticService:
    def __init__(self, pending_approval_ids: tuple[str, ...] = ()) -> None:
        self.calls = 0
        self.pending_approval_ids = pending_approval_ids

    def execute(self, prompt: str) -> DiagnosticAgentResult:
        self.calls += 1
        return DiagnosticAgentResult(
            answer=f"diagnosis for {prompt}",
            tool_trace=(),
            pending_approval_ids=self.pending_approval_ids,
        )


def test_diagnostic_result_is_reused_from_cache() -> None:
    delegate = StubDiagnosticService()
    service = CachedDiagnosticAgentService(delegate, FakeCache())

    first = service.execute("Check DF-01")
    second = service.execute("  check   DF-01 ")

    assert first == second
    assert delegate.calls == 1


def test_pending_approval_is_never_cached() -> None:
    delegate = StubDiagnosticService(("approval-1",))
    service = CachedDiagnosticAgentService(delegate, FakeCache())

    service.execute("Stop DF-01")
    service.execute("Stop DF-01")

    assert delegate.calls == 2
