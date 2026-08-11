from typing import Protocol

from fabcopilot.domain.equipment import EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument, KnowledgeSearchResult


class KnowledgeRepository(Protocol):
    def save(self, document: KnowledgeDocument, embedding: list[float]) -> None: ...

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        equipment_type: EquipmentType,
        limit: int,
    ) -> list[KnowledgeSearchResult]: ...
