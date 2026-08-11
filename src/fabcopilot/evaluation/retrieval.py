from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from time import perf_counter

from sqlalchemy import delete
from sqlalchemy.orm import Session

from fabcopilot.application.ports.embedding_provider import EmbeddingProvider
from fabcopilot.application.services.knowledge import IndexKnowledgeDocumentService
from fabcopilot.config import Settings
from fabcopilot.domain.equipment import EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument
from fabcopilot.infrastructure.database import create_database_engine
from fabcopilot.infrastructure.embeddings import (
    FastEmbedEmbeddingProvider,
    HashingEmbeddingProvider,
)
from fabcopilot.infrastructure.models import KnowledgeDocumentRecord
from fabcopilot.infrastructure.repositories.sqlalchemy_knowledge_repository import (
    SqlAlchemyKnowledgeRepository,
)


@dataclass(frozen=True)
class RetrievalMetrics:
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mean_reciprocal_rank: float
    mean_latency_ms: float
    p95_latency_ms: float


@dataclass(frozen=True)
class RetrievalEvaluationResult:
    provider: str
    model: str
    documents: int
    queries: int
    indexing_seconds: float
    lexical: RetrievalMetrics
    vector: RetrievalMetrics
    hybrid: RetrievalMetrics
    hybrid_top1_failures: tuple[RetrievalFailure, ...]


@dataclass(frozen=True)
class RetrievalFailure:
    case_id: str
    query: str
    expected: tuple[str, ...]
    actual_top_5: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    relevant_document_ids: frozenset[str]


def load_dataset(
    path: Path,
) -> tuple[tuple[KnowledgeDocument, ...], tuple[RetrievalCase, ...]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    documents = tuple(
        KnowledgeDocument(
            document_id=item["document_id"],
            equipment_type=EquipmentType(item["equipment_type"]),
            title=item["title"],
            content=item["content"],
            source=item["source"],
        )
        for item in raw["documents"]
    )
    cases = tuple(
        RetrievalCase(
            case_id=item["case_id"],
            query=item["query"],
            relevant_document_ids=frozenset(item["relevant_document_ids"]),
        )
        for item in raw["queries"]
    )
    return documents, cases


def evaluate_retrieval(
    dataset_path: Path,
    provider_name: str,
    model_name: str,
) -> RetrievalEvaluationResult:
    documents, cases = load_dataset(dataset_path)
    provider = _create_provider(provider_name, model_name)
    engine = create_database_engine(Settings().database_url)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    repository = SqlAlchemyKnowledgeRepository(session)
    try:
        # Evaluate against an isolated corpus while rolling the deletion back at
        # the end, so local demo data neither skews metrics nor gets destroyed.
        session.execute(delete(KnowledgeDocumentRecord))
        indexer = IndexKnowledgeDocumentService(repository, provider)
        indexing_started = perf_counter()
        for document in documents:
            indexer.execute(document)
        indexing_seconds = perf_counter() - indexing_started

        rankings: dict[str, list[tuple[RetrievalCase, list[str], float]]] = {
            "lexical": [],
            "vector": [],
            "hybrid": [],
        }
        for case in cases:
            query_embedding = provider.embed(case.query)

            started = perf_counter()
            lexical_records = session.scalars(
                repository._lexical_statement(  # noqa: SLF001
                    case.query,
                    EquipmentType.DIFFUSION_FURNACE,
                    5,
                )
            ).all()
            rankings["lexical"].append(
                (
                    case,
                    [record.document_id for record in lexical_records],
                    (perf_counter() - started) * 1000,
                )
            )

            started = perf_counter()
            vector_records = session.scalars(
                repository._vector_statement(  # noqa: SLF001
                    query_embedding,
                    EquipmentType.DIFFUSION_FURNACE,
                    5,
                )
            ).all()
            rankings["vector"].append(
                (
                    case,
                    [record.document_id for record in vector_records],
                    (perf_counter() - started) * 1000,
                )
            )

            started = perf_counter()
            hybrid_results = repository.hybrid_search(
                query=case.query,
                query_embedding=query_embedding,
                equipment_type=EquipmentType.DIFFUSION_FURNACE,
                limit=5,
            )
            rankings["hybrid"].append(
                (
                    case,
                    [result.document.document_id for result in hybrid_results],
                    (perf_counter() - started) * 1000,
                )
            )

        return RetrievalEvaluationResult(
            provider=provider_name,
            model=getattr(provider, "model_name", "deterministic-feature-hashing"),
            documents=len(documents),
            queries=len(cases),
            indexing_seconds=indexing_seconds,
            lexical=_calculate_metrics(rankings["lexical"]),
            vector=_calculate_metrics(rankings["vector"]),
            hybrid=_calculate_metrics(rankings["hybrid"]),
            hybrid_top1_failures=tuple(
                RetrievalFailure(
                    case_id=case.case_id,
                    query=case.query,
                    expected=tuple(sorted(case.relevant_document_ids)),
                    actual_top_5=tuple(ranking),
                )
                for case, ranking, _ in rankings["hybrid"]
                if not ranking or ranking[0] not in case.relevant_document_ids
            ),
        )
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
        engine.dispose()


def _create_provider(provider_name: str, model_name: str) -> EmbeddingProvider:
    if provider_name == "hashing":
        return HashingEmbeddingProvider()
    if provider_name == "fastembed":
        return FastEmbedEmbeddingProvider(model_name=model_name)
    raise ValueError(f"unsupported provider: {provider_name}")


def _calculate_metrics(
    rows: list[tuple[RetrievalCase, list[str], float]],
) -> RetrievalMetrics:
    recalls: dict[int, list[float]] = {1: [], 3: [], 5: []}
    reciprocal_ranks: list[float] = []
    latencies: list[float] = []
    for case, ranking, latency_ms in rows:
        for k in recalls:
            retrieved = set(ranking[:k])
            recalls[k].append(
                len(retrieved & case.relevant_document_ids)
                / len(case.relevant_document_ids)
            )
        reciprocal_rank = 0.0
        for rank, document_id in enumerate(ranking, start=1):
            if document_id in case.relevant_document_ids:
                reciprocal_rank = 1.0 / rank
                break
        reciprocal_ranks.append(reciprocal_rank)
        latencies.append(latency_ms)

    ordered_latencies = sorted(latencies)
    p95_index = max(0, math.ceil(len(ordered_latencies) * 0.95) - 1)
    return RetrievalMetrics(
        recall_at_1=mean(recalls[1]),
        recall_at_3=mean(recalls[3]),
        recall_at_5=mean(recalls[5]),
        mean_reciprocal_rank=mean(reciprocal_ranks),
        mean_latency_ms=mean(latencies),
        p95_latency_ms=ordered_latencies[p95_index],
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=project_root / "evals" / "retrieval_cases.json",
    )
    parser.add_argument(
        "--provider",
        choices=("hashing", "fastembed"),
        default="hashing",
    )
    parser.add_argument(
        "--model",
        default=Settings().embedding_model,
    )
    args = parser.parse_args()
    result = evaluate_retrieval(args.dataset, args.provider, args.model)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
