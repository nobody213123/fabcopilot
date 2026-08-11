import hashlib
from typing import Protocol

from fabcopilot.application.ports.cache import JsonCache
from fabcopilot.domain.agent import (
    AgentToolTrace,
    DiagnosticAgentResult,
    DiagnosticEvidence,
)


class DiagnosticService(Protocol):
    def execute(self, prompt: str) -> DiagnosticAgentResult: ...


class CachedDiagnosticAgentService:
    def __init__(
        self,
        delegate: DiagnosticService,
        cache: JsonCache,
        ttl_seconds: int = 300,
        cache_namespace: str = "diagnosis:v2",
    ) -> None:
        self._delegate = delegate
        self._cache = cache
        self._ttl_seconds = ttl_seconds
        self._cache_namespace = cache_namespace

    def execute(self, prompt: str) -> DiagnosticAgentResult:
        knowledge_version = self._cache.get_version("knowledge")
        cache_key = self._cache_key(prompt, knowledge_version)
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

    def _cache_key(self, prompt: str, knowledge_version: int) -> str:
        normalized = " ".join(prompt.split()).casefold()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"{self._cache_namespace}:kb{knowledge_version}:{digest}"

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
            "evidence": [
                {
                    "kind": item.kind,
                    "reference_id": item.reference_id,
                    "source": item.source,
                    "summary": item.summary,
                }
                for item in result.evidence
            ],
            "missing_evidence": list(result.missing_evidence),
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
        raw_evidence = value.get("evidence", [])
        if not isinstance(raw_evidence, list):
            raise ValueError("cached evidence is invalid")
        evidence = tuple(
            DiagnosticEvidence(
                kind=str(item["kind"]),
                reference_id=str(item["reference_id"]),
                source=str(item["source"]),
                summary=str(item["summary"]),
            )
            for item in raw_evidence
            if isinstance(item, dict)
        )
        missing_evidence = value.get("missing_evidence", [])
        if not isinstance(missing_evidence, list):
            raise ValueError("cached missing evidence is invalid")
        return DiagnosticAgentResult(
            answer=str(value["answer"]),
            tool_trace=tuple(trace),
            pending_approval_ids=tuple(str(item) for item in pending),
            evidence=evidence,
            missing_evidence=tuple(str(item) for item in missing_evidence),
        )
