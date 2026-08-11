from dataclasses import dataclass

from sqlalchemy import Select, desc, func, select
from sqlalchemy.orm import Session

from fabcopilot.domain.equipment import EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument, KnowledgeSearchResult
from fabcopilot.infrastructure.models import KnowledgeDocumentRecord

_RRF_K = 60


@dataclass
class _RankedDocument:
    record: KnowledgeDocumentRecord
    lexical_rank: int | None = None
    vector_rank: int | None = None

    @property
    def score(self) -> float:
        score = 0.0
        if self.lexical_rank is not None:
            score += 1.0 / (_RRF_K + self.lexical_rank)
        if self.vector_rank is not None:
            score += 1.0 / (_RRF_K + self.vector_rank)
        return score


class SqlAlchemyKnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, document: KnowledgeDocument, embedding: list[float]) -> None:
        self._session.merge(
            KnowledgeDocumentRecord(
                document_id=document.document_id,
                equipment_type=document.equipment_type.value,
                title=document.title,
                content=document.content,
                source=document.source,
                embedding=embedding,
            )
        )
        self._session.flush()

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        equipment_type: EquipmentType,
        limit: int,
    ) -> list[KnowledgeSearchResult]:
        candidate_limit = max(limit * 4, 20)
        ranked_documents: dict[str, _RankedDocument] = {}

        lexical_records = self._session.scalars(
            self._lexical_statement(query, equipment_type, candidate_limit)
        ).all()
        for rank, record in enumerate(lexical_records, start=1):
            ranked_documents[record.document_id] = _RankedDocument(
                record=record,
                lexical_rank=rank,
            )

        vector_records = self._session.scalars(
            self._vector_statement(query_embedding, equipment_type, candidate_limit)
        ).all()
        for rank, record in enumerate(vector_records, start=1):
            ranked = ranked_documents.setdefault(
                record.document_id,
                _RankedDocument(record=record),
            )
            ranked.vector_rank = rank

        ordered = sorted(
            ranked_documents.values(),
            key=lambda item: (-item.score, item.record.document_id),
        )[:limit]
        return [self._to_search_result(item) for item in ordered]

    @staticmethod
    def _lexical_statement(
        query: str,
        equipment_type: EquipmentType,
        limit: int,
    ) -> Select[tuple[KnowledgeDocumentRecord]]:
        ts_query = func.plainto_tsquery("simple", query)
        rank = func.ts_rank_cd(KnowledgeDocumentRecord.search_vector, ts_query)
        return (
            select(KnowledgeDocumentRecord)
            .where(
                KnowledgeDocumentRecord.equipment_type == equipment_type.value,
                KnowledgeDocumentRecord.search_vector.op("@@")(ts_query),
            )
            .order_by(desc(rank), KnowledgeDocumentRecord.document_id)
            .limit(limit)
        )

    @staticmethod
    def _vector_statement(
        query_embedding: list[float],
        equipment_type: EquipmentType,
        limit: int,
    ) -> Select[tuple[KnowledgeDocumentRecord]]:
        distance = KnowledgeDocumentRecord.embedding.cosine_distance(query_embedding)
        return (
            select(KnowledgeDocumentRecord)
            .where(KnowledgeDocumentRecord.equipment_type == equipment_type.value)
            .order_by(distance, KnowledgeDocumentRecord.document_id)
            .limit(limit)
        )

    @staticmethod
    def _to_search_result(ranked: _RankedDocument) -> KnowledgeSearchResult:
        record = ranked.record
        return KnowledgeSearchResult(
            document=KnowledgeDocument(
                document_id=record.document_id,
                equipment_type=EquipmentType(record.equipment_type),
                title=record.title,
                content=record.content,
                source=record.source,
            ),
            score=ranked.score,
            lexical_rank=ranked.lexical_rank,
            vector_rank=ranked.vector_rank,
        )
