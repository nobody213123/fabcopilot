import hashlib
from typing import Protocol

from fabcopilot.application.ports.cache import JsonCache
from fabcopilot.domain.agent import AgentToolTrace, DiagnosticAgentResult


class DiagnosticService(Protocol):
    def execute(self, prompt: str) -> DiagnosticAgentResult: ...


class CachedDiagnosticAgentService:
    def __init__(
        self,
        delegate: DiagnosticService,
        cache: JsonCache,
        ttl_seconds: int = 300,
    ) -> None:
        self._delegate = delegate
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    def execute(self, prompt: str) -> DiagnosticAgentResult:
        cache_key = self._cache_key(prompt)
        cached = self._cache.get_json(cache_key)
        if cached is not None:
            try:
                return self._deserialize(cached)
            except (KeyError, TypeError, ValueError):
                # Ignore incompatible entries left by an older deployment.
                pass

        result = self._delegate.execute(prompt)
        # Approval IDs represent live workflow state and must never be replayed.
        if not result.pending_approval_ids:
            self._cache.set_json(
                cache_key,
                self._serialize(result),
                self._ttl_seconds,
            )
        return result

    @staticmethod
    def _cache_key(prompt: str) -> str:
        normalized = " ".join(prompt.split()).casefold()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"diagnosis:v1:{digest}"

    @staticmethod
    def _serialize(result: DiagnosticAgentResult) -> dict[str, object]:
        return {
            "answer": result.answer,
            "tool_trace": [
                {
                    "name": item.name,
                    "arguments": item.arguments,
                    "output": item.output,
                }
                for item in result.tool_trace
            ],
            "pending_approval_ids": list(result.pending_approval_ids),
        }

    @staticmethod
    def _deserialize(value: dict[str, object]) -> DiagnosticAgentResult:
        raw_trace = value.get("tool_trace", [])
        if not isinstance(raw_trace, list):
            raise ValueError("cached diagnostic trace is invalid")

        trace: list[AgentToolTrace] = []
        for item in raw_trace:
            if not isinstance(item, dict):
                raise ValueError("cached diagnostic trace item is invalid")
            arguments = item.get("arguments", {})
            output = item.get("output", {})
            if not isinstance(arguments, dict) or not isinstance(output, dict):
                raise ValueError("cached diagnostic tool data is invalid")
            trace.append(
                AgentToolTrace(
                    name=str(item["name"]),
                    arguments=arguments,
                    output=output,
                )
            )

        pending = value.get("pending_approval_ids", [])
        if not isinstance(pending, list):
            raise ValueError("cached approval IDs are invalid")
        return DiagnosticAgentResult(
            answer=str(value["answer"]),
            tool_trace=tuple(trace),
            pending_approval_ids=tuple(str(item) for item in pending),
        )
